"""Formal schema and validation of the JSON model that ExerPy's analyses read.

The JSON document fed into :meth:`exerpy.ExergyAnalysis.from_json` (and produced by
the TESPy, Aspen and EBSILON parsers) is described here as ``msgspec`` structs.

The schema covers only the fields ExerPy reads. The keys of each component type are
declared next to the code that reads them, as the ``Input`` struct nested in the
component class (see :class:`exerpy.components.component.Component`); this module
collects them from the component registry, so custom components are covered too. The
exports also carry what the simulators report besides (efficiencies, units, fluid ids,
results of an earlier analysis, ...); ExerPy ignores those, and so does the validation.
Each field below notes where ExerPy uses it.

The validation does not convert units. Its bounds hold in SI, so ExerPy converts the values
with :func:`exerpy.units.to_SI` before it validates them. Validation happens in two passes:

1. **Structural**, done by ``msgspec`` while decoding: required keys, types, the
   ``kind`` tag of each connection and physical bounds (positive temperatures, mass
   fractions in [0, 1], ...).
2. **Semantic**, done by :func:`validate` on the decoded structs: rules that span
   several fields or sections and so cannot be written as a type, e.g. that each
   component type is registered, that no two streams enter the same inlet of a
   component, that ``split_physical_exergy`` has the ``e_T``/``e_M`` values it
   needs, or that each unit given (``"T_unit": "degC"``) is known and of the right
   kind. A value without a unit is in SI.

All problems are collected and reported together.

Example
-------
>>> from exerpy.schema import validate
>>> model = validate(open("example.json", "rb").read())  # doctest: +SKIP
>>> model.connections["1"].m  # doctest: +SKIP
637.86...

The JSON Schema of the format is returned by :func:`json_schema`.
"""

from __future__ import annotations

import functools
from typing import Annotated
from typing import Any
from typing import Literal
from typing import Union

import msgspec
from msgspec import UNSET
from msgspec import Meta
from msgspec import Struct
from msgspec import UnsetType

from . import units
from .components.component import Component
from .components.component import component_registry
from .logger import logger
from .quantities import Composition
from .quantities import ConnectorIndex
from .quantities import Fraction
from .quantities import MassFlow
from .quantities import Pressure
from .quantities import SpecificExergy
from .quantities import Temperature

__all__ = [
    "AmbientConditions",
    "Connection",
    "ExerpyInput",
    "HeatConnection",
    "InputValidationError",
    "Issue",
    "MaterialConnection",
    "OtherConnection",
    "PowerConnection",
    "Settings",
    "check",
    "input_struct",
    "json_schema",
    "validate",
]

# ---------------------------------------------------------------------------------------
# Sections
# ---------------------------------------------------------------------------------------


class AmbientConditions(Struct, kw_only=True):
    """Dead state of the analysis. Values may instead be passed to ``from_json``."""

    Tamb: Temperature | UnsetType = UNSET
    pamb: Pressure | UnsetType = UNSET


class Settings(Struct, kw_only=True):
    """Analysis options. Arguments to ``from_json`` take precedence over these."""

    split_physical_exergy: bool | None = None
    chemExLib: Literal["Ahrendts"] | None = None


class _ConnectionBase(Struct, kw_only=True, tag_field="kind"):
    """Fields common to every connection. ``kind`` selects the subclass."""

    # The keys must be present; null marks the system boundary.
    source_component: str | None
    target_component: str | None
    # The port of the component the connection leaves / enters.
    source_connector: ConnectorIndex | None = None
    target_connector: ConnectorIndex | None = None
    # Boundary detection (EBSILON: type 1 is a boundary value).
    source_component_type: int | str | None | UnsetType = UNSET


class MaterialConnection(_ConnectionBase, tag="material"):
    """A stream of matter."""

    # Read by every component and by the exergy flow calculation.
    m: MassFlow
    T: Temperature
    e_PH: SpecificExergy
    # Read by some components (h: power and heat balances; p: valves) and by costing.
    # Required for every stream, so a component never finds them missing.
    h: Annotated[float, Meta(description="Specific enthalpy in J/kg")]
    p: Pressure
    # Needed with split_physical_exergy.
    e_T: SpecificExergy | None | UnsetType = UNSET
    e_M: SpecificExergy | None | UnsetType = UNSET
    # Chemical exergy, or the composition it is computed from with chemExLib.
    e_CH: SpecificExergy | None | UnsetType = UNSET
    mass_composition: Composition | UnsetType = UNSET
    molar_composition: Composition | UnsetType = UNSET
    # exerpy.costing: vapour quality and volume flow for equipment sizing.
    x: float | None | UnsetType = UNSET
    v: float | None | UnsetType = UNSET
    VM: float | None | UnsetType = UNSET


class PowerConnection(_ConnectionBase, tag="power"):
    """Mechanical or electrical power; its exergy equals ``energy_flow``."""

    energy_flow: Annotated[float, Meta(description="Power in W")]


class HeatConnection(_ConnectionBase, tag="heat"):
    """Heat, in W. Its exergy is derived from the attached component."""

    energy_flow: float | None | UnsetType = UNSET


class OtherConnection(_ConnectionBase, tag="other"):
    """A logical connection (e.g. EBSILON control lines), carried but not analysed."""


Connection = Union[MaterialConnection, PowerConnection, HeatConnection, OtherConnection]


class ExerpyInput(Struct, kw_only=True):
    """The complete input document of an exergy analysis."""

    # Component type -> component name -> its ``Input`` struct (see :func:`input_struct`).
    components: dict[str, dict[str, Component.Input]]
    connections: dict[str, Connection]
    ambient_conditions: AmbientConditions
    settings: Settings = msgspec.field(default_factory=Settings)


# ---------------------------------------------------------------------------------------
# Issues and errors
# ---------------------------------------------------------------------------------------


class Issue(Struct, frozen=True):
    """One validation finding, located by a JSONPath-like ``path``."""

    severity: Literal["error", "warning"]
    path: str
    message: str

    def __str__(self) -> str:
        return f"{self.severity}: {self.message} - at `{self.path}`"


class InputValidationError(ValueError):
    """Raised when the input fails validation. ``issues`` holds every finding."""

    def __init__(self, issues: list[Issue]):
        self.issues = issues
        errors = [i for i in issues if i.severity == "error"]
        lines = "\n".join(f"  - {i}" for i in errors)
        super().__init__(f"Invalid ExerPy input ({len(errors)} error(s)):\n{lines}")


# ---------------------------------------------------------------------------------------
# Semantic checks
# ---------------------------------------------------------------------------------------

_DEPRECATED_TYPES = {"Condenser": "HeatExchanger"}
_COMPOSITION_TOL = 1e-3


def _p(*parts: str) -> str:
    """Build a path like ``$.connections['3'].m``."""
    out = "$"
    for part in parts:
        out += part if part.startswith("[") else f".{part}"
    return out


def _key(k: str) -> str:
    return f"[{k!r}]"


def input_struct(component_type: str) -> type[Component.Input]:
    """The ``Input`` struct of a component type, as found in the component registry.

    Deprecated types resolve to the type they are read as; an unknown type, or a
    registered class that declares no ``Input``, gets the base ``Component.Input``.
    """
    cls = component_registry.items.get(_DEPRECATED_TYPES.get(component_type, component_type))
    return getattr(cls, "Input", Component.Input)


def _semantic_issues(
    model: ExerpyInput,
    Tamb: float | None,
    pamb: float | None,
    chemExLib: str | None,
    split_physical_exergy: bool | None,
) -> list[Issue]:
    issues: list[Issue] = []
    err = lambda path, msg: issues.append(Issue("error", path, msg))  # noqa: E731
    warn = lambda path, msg: issues.append(Issue("warning", path, msg))  # noqa: E731

    # --- ambient conditions ------------------------------------------------------------
    amb = model.ambient_conditions
    T0 = Tamb if Tamb is not None else (None if amb.Tamb is UNSET else amb.Tamb)
    p0 = pamb if pamb is not None else (None if amb.pamb is UNSET else amb.pamb)
    if T0 is None:
        err(_p("ambient_conditions"), "Tamb is required, in the JSON or as an argument")
    if p0 is None:
        err(_p("ambient_conditions"), "pamb is required, in the JSON or as an argument")

    # --- components --------------------------------------------------------------------
    registered = set(component_registry.items) - {"Component"}  # the base class is not a type
    owner: dict[str, str] = {}  # component name -> section it was first defined in
    analysed: set[str] = set()  # names of components the analysis will instantiate
    for ctype, instances in model.components.items():
        tpath = _p("components", _key(ctype))
        if ctype in _DEPRECATED_TYPES:
            warn(tpath, f"component type {ctype!r} is deprecated and read as {_DEPRECATED_TYPES[ctype]!r}")
        elif ctype not in registered:
            err(tpath, f"unknown component type {ctype!r}")
            continue
        for cname, comp in instances.items():
            cpath = tpath + _key(cname)
            if comp.name != cname:
                err(cpath + ".name", f"name {comp.name!r} differs from its key {cname!r}")
            if cname in owner:
                err(cpath, f"component name {cname!r} is already used in section {owner[cname]!r}")
            else:
                owner[cname] = ctype
            analysed.add(cname)

    # --- connections -------------------------------------------------------------------
    ports: dict[tuple[str, str, int | None], str] = {}
    attached: set[str] = set()
    material: dict[str, MaterialConnection] = {}
    for key, conn in model.connections.items():
        cpath = _p("connections", _key(key))
        if conn.source_component is None and conn.target_component is None:
            warn(cpath, "connection is attached to no component and is ignored")
        for side, comp, port in (
            ("source", conn.source_component, conn.source_connector),
            ("target", conn.target_component, conn.target_connector),
        ):
            if comp is None:
                continue
            if comp in analysed:
                attached.add(comp)
                # Components address material streams by port (inl[0], outl[1], ...);
                # heat and power links are found by kind, so a null port is fine there.
                if port is None and isinstance(conn, MaterialConnection):
                    warn(cpath + f".{side}_connector", f"{side}_connector is null although {comp!r} is a component")
                other = ports.setdefault((side, comp, port), key)
                if other != key:
                    direction = "outlet" if side == "source" else "inlet"
                    err(
                        cpath + f".{side}_connector",
                        f"{direction} {port} of {comp!r} is already used by connection {other!r}",
                    )
        if isinstance(conn, MaterialConnection):
            material[key] = conn
            for field in ("mass_composition", "molar_composition"):
                comp_ = getattr(conn, field)
                if comp_ is not UNSET and comp_ and abs(sum(comp_.values()) - 1) > _COMPOSITION_TOL:
                    hint = " (H2O and H2OG are both listed)" if {"H2O", "H2OG"} <= comp_.keys() else ""
                    warn(cpath + f".{field}", f"fractions sum to {sum(comp_.values()):.4f}, not 1{hint}")

    for cname in sorted(analysed - attached):
        warn(_p("components", _key(owner[cname]), _key(cname)), "component has no connections")

    # --- settings that depend on the streams -------------------------------------------
    # Resolved in the same order as exerpy.analyses._process_json: argument, then
    # settings, then detection from the data.
    split = split_physical_exergy if split_physical_exergy is not None else model.settings.split_physical_exergy
    lib = chemExLib if chemExLib is not None else model.settings.chemExLib
    has_chem = any(c.e_CH not in (None, UNSET) for c in material.values())
    if split:
        missing = [k for k, c in material.items() if c.e_T in (None, UNSET) or c.e_M in (None, UNSET)]
        for k in missing:
            err(_p("connections", _key(k)), "split_physical_exergy is enabled but e_T or e_M is missing")
    if lib and not has_chem:
        for k, c in material.items():
            if c.mass_composition is UNSET:
                err(_p("connections", _key(k)), f"chemExLib={lib!r} needs mass_composition to compute e_CH")

    return issues


def _unit_issues(data: dict) -> list[Issue]:
    """Each unit given for a value of :data:`exerpy.units.SI_UNITS` has to be known and of the right kind."""
    issues: list[Issue] = []
    for entry, path in units.entries(data):
        for key, si in units.SI_UNITS.items():
            unit = entry.get(f"{key}_unit")
            if unit is None:
                continue
            try:
                units.check_unit(unit, si)
            except ValueError as exc:
                issues.append(Issue("error", f"{path}.{key}_unit", str(exc)))
    return issues


# ---------------------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------------------


def _enc_hook(obj: Any) -> Any:
    # NumPy scalars from the parsers: not Python numbers, but have .item().
    if hasattr(obj, "item"):
        return obj.item()
    raise NotImplementedError(f"Objects of type {type(obj)} are not supported")


class _Envelope(Struct, kw_only=True):
    """:class:`ExerpyInput` with components and connections left undecoded.

    msgspec reports a dictionary key in an error path as ``[...]``. Decoding each
    component and connection on its own lets the path name the actual key, and lets
    the structural errors of all of them be reported together.
    """

    components: dict[str, msgspec.Raw]
    connections: dict[str, msgspec.Raw]
    ambient_conditions: AmbientConditions
    settings: Settings = msgspec.field(default_factory=Settings)


_decode_envelope = msgspec.json.Decoder(_Envelope).decode
_decode_section = msgspec.json.Decoder(dict[str, msgspec.Raw]).decode
_decode_connection = msgspec.json.Decoder(Connection).decode
_decode_any = msgspec.json.Decoder().decode

# Value type of the dict-valued fields, to find the key msgspec elides as ``[...]``.
_DICT_FIELDS = {"mass_composition": Fraction, "molar_composition": Fraction}


@functools.cache
def _component_decoder(struct: type) -> msgspec.json.Decoder:
    return msgspec.json.Decoder(struct)


def _fits(value: Any, type_: Any) -> bool:
    try:
        msgspec.convert(value, type_)
    except msgspec.ValidationError:
        return False
    return True


def _structural_issue(exc: msgspec.ValidationError, prefix: str = "$", raw: msgspec.Raw | None = None) -> Issue:
    """Turn a msgspec error into an :class:`Issue` located below ``prefix``."""
    msg, _, tail = str(exc).rpartition(" - at `")
    if not msg:
        msg, tail = str(exc), "$"
    tail = tail.rstrip("`")[1:]  # drop the leading "$"
    for field, value_type in _DICT_FIELDS.items():
        marker = f".{field}[...]"
        if raw is not None and tail.startswith(marker):
            values = _decode_any(raw).get(field, {})
            bad = next((k for k, v in values.items() if not _fits(v, value_type)), None)
            if bad is not None:
                tail = f".{field}" + _key(bad) + tail[len(marker) :]
    return Issue("error", prefix + tail, msg)


def check(
    data: bytes | str | dict,
    *,
    Tamb: float | None = None,
    pamb: float | None = None,
    chemExLib: str | None = None,
    split_physical_exergy: bool | None = None,
) -> tuple[ExerpyInput | None, list[Issue]]:
    """Validate without raising: return the model (``None`` if invalid) and all issues.

    Parameters are those of :func:`validate`.
    """
    if isinstance(data, dict):
        try:
            buf = msgspec.json.encode(data, enc_hook=_enc_hook)
        except (TypeError, NotImplementedError, OverflowError) as exc:
            return None, [Issue("error", "$", f"data is not JSON-serialisable: {exc}")]
    else:
        buf = data.encode() if isinstance(data, str) else data
    try:
        env = _decode_envelope(buf)
    except msgspec.ValidationError as exc:
        return None, [_structural_issue(exc)]
    except msgspec.DecodeError as exc:
        return None, [Issue("error", "$", f"malformed JSON: {exc}")]

    structural: list[Issue] = []
    components: dict[str, dict[str, Component.Input]] = {}
    for ctype, section in env.components.items():
        spath = _p("components", _key(ctype))
        decode_component = _component_decoder(input_struct(ctype)).decode
        try:
            instances = _decode_section(section)
        except msgspec.ValidationError as exc:
            structural.append(_structural_issue(exc, spath))
            continue
        components[ctype] = {}
        for cname, item in instances.items():
            try:
                components[ctype][cname] = decode_component(item)
            except msgspec.ValidationError as exc:
                structural.append(_structural_issue(exc, spath + _key(cname), item))
    connections: dict[str, Connection] = {}
    for key, item in env.connections.items():
        try:
            connections[key] = _decode_connection(item)
        except msgspec.ValidationError as exc:
            structural.append(_structural_issue(exc, _p("connections", _key(key)), item))
    if structural:
        return None, structural

    model = ExerpyInput(
        components=components,
        connections=connections,
        ambient_conditions=env.ambient_conditions,
        settings=env.settings,
    )
    issues = _semantic_issues(model, Tamb, pamb, chemExLib, split_physical_exergy)
    issues += _unit_issues(data if isinstance(data, dict) else _decode_any(buf))
    return (None if any(i.severity == "error" for i in issues) else model), issues


def validate(
    data: bytes | str | dict,
    *,
    Tamb: float | None = None,
    pamb: float | None = None,
    chemExLib: str | None = None,
    split_physical_exergy: bool | None = None,
    log_warnings: bool = True,
) -> ExerpyInput:
    """Validate an ExerPy input document and return it as typed structs.

    Parameters
    ----------
    data : bytes, str or dict
        The JSON document, or the dictionary decoded from it (as the parsers build).
    Tamb, pamb, chemExLib, split_physical_exergy : optional
        The overrides that will be passed to the analysis; they take precedence over
        the JSON, as in :meth:`exerpy.ExergyAnalysis.from_json`.
    log_warnings : bool
        Log warnings through the ExerPy logger.

    Returns
    -------
    ExerpyInput
        The validated document. Unknown keys are not part of it; the analysis keeps
        working on the original dictionary.

    Raises
    ------
    InputValidationError
        A subclass of ``ValueError``. ``issues`` lists every finding, warnings included.
    """
    model, issues = check(data, Tamb=Tamb, pamb=pamb, chemExLib=chemExLib, split_physical_exergy=split_physical_exergy)
    if model is None:
        raise InputValidationError(issues)
    if log_warnings:
        for issue in issues:
            logger.warning(str(issue))
    return model


def json_schema() -> dict:
    """JSON Schema (draft 2020-12) of the input, for editors and other tools.

    ``components`` lists each component type registered when this is called, with the
    fields of its ``Input`` struct.
    """
    types = sorted((set(component_registry.items) - {"Component"}) | set(_DEPRECATED_TYPES))
    structs = {t: input_struct(t) for t in types}
    unique = list(dict.fromkeys(structs.values()))
    (root, *refs), defs = msgspec.json.schema_components([ExerpyInput, *unique], ref_template="#/$defs/{name}")
    # The nested classes are all named Input, so msgspec names their definitions by
    # module and qualified name; name them by the class instead (HeatExchangerInput).
    names = {s_: "".join(s_.__qualname__.split(".")[-2:]) for s_ in unique}
    rename = {r["$ref"].rpartition("/")[2]: names[s_] for s_, r in zip(unique, refs, strict=True)}
    text = msgspec.json.encode(defs).decode()
    for old, new in rename.items():
        text = text.replace(f'"#/$defs/{old}"', f'"#/$defs/{new}"')
    defs = {rename.get(k, k): v for k, v in msgspec.json.decode(text).items()}
    for name in names.values():
        defs[name]["title"] = name
    defs["ExerpyInput"]["properties"]["components"] = {
        "type": "object",
        "properties": {
            t: {"type": "object", "additionalProperties": {"$ref": f"#/$defs/{names[struct]}"}}
            for t, struct in structs.items()
        },
        "additionalProperties": False,
    }
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "ExerPy input",
        **root,
        "$defs": defs,
    }
