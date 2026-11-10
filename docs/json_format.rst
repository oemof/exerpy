.. _json_format_label:

###########
JSON format
###########

ExerPy keeps a model in a JSON file. The parsers for TESPy, Ebsilon and Aspen write it with
:meth:`~exerpy.analyses.ExergyAnalysis.export_to_json`, and
:meth:`~exerpy.analyses.ExergyAnalysis.from_json` reads it back. You can also write such a file
yourself, for example to analyse a model from a simulator that ExerPy has no parser for. This
page describes the format and how ExerPy checks it.

*********
Structure
*********

A file has four sections:

.. list-table::
    :header-rows: 1
    :widths: 25 75

    * - Section
      - Content
    * - ``components``
      - The components, grouped by their type, e.g. ``Compressor`` or ``HeatExchanger``. Each
        component is stored under its name.
    * - ``connections``
      - The streams between the components, stored under their names.
    * - ``ambient_conditions``
      - The ambient temperature ``Tamb`` and pressure ``pamb`` at which the exergies of the file
        were computed. Both may instead be passed to ``from_json`` if the file has none; a passed
        value that differs from the file raises an error.
    * - ``settings``
      - Optional: ``split_physical_exergy`` and ``chemExLib``. Arguments passed to ``from_json``
        take precedence.

A compressor that takes in air and is driven by a motor outside the system looks like this:

.. code-block:: json

    {
        "components": {
            "Compressor": {
                "COMP": {"name": "COMP"}
            }
        },
        "connections": {
            "1": {
                "kind": "material",
                "source_component": null,
                "target_component": "COMP",
                "target_connector": 0,
                "m": 10.0, "T": 288.15, "p": 101300.0, "h": 15156.0, "e_PH": 0.0
            },
            "2": {
                "kind": "material",
                "source_component": "COMP",
                "source_connector": 0,
                "target_component": null,
                "m": 10.0, "T": 655.0, "p": 1551000.0, "h": 400000.0, "e_PH": 362000.0
            },
            "W1": {
                "kind": "power",
                "source_component": null,
                "target_component": "COMP",
                "target_connector": 1,
                "energy_flow": 3848440.0
            }
        },
        "ambient_conditions": {"Tamb": 288.15, "pamb": 101300.0},
        "settings": {"split_physical_exergy": false}
    }

**********
Components
**********

Every component needs its ``name``, which has to be the same as the key it is stored under.
Some types read further values:

.. list-table::
    :header-rows: 1
    :widths: 30 70

    * - Type
      - Further values
    * - ``HeatExchanger``
      - ``dissipative`` (``true`` or ``false`` to override the automatic choice), ``kA``, or
        ``kA`` inside ``parameters``
    * - ``SimpleHeatExchanger``
      - ``dissipative``, ``T_hot`` and ``T_cold``, the temperature of the heat source or
        consumer
    * - ``SteamGenerator``
      - ``T_hot``, the temperature of the heat source
    * - ``Mixer``, ``Splitter``
      - ``num_branches`` is accepted but not needed: a header counts a stream of a
        ``ParabolicTrough`` as often as the trough's ``num_branches``, every other stream once. A
        value that none of its streams has gives a warning
    * - ``Heliostatfield``
      - ``Q_Solar``, the incident solar heat
    * - ``ParabolicTrough``
      - ``Q_Solar`` and ``num_branches``, the number of identical parallel branches it stands for

All other values of a component, such as the efficiencies a simulator reports, are kept but not
checked.

***********
Connections
***********

``kind`` says what a connection carries: ``material``, ``power``, ``heat`` or ``other``.
Every connection names its ``source_component`` and ``target_component``. Use ``null`` where it
crosses the system boundary. ``source_connector`` and ``target_connector`` give the port of the
component, counted from 0.

.. list-table::
    :header-rows: 1
    :widths: 15 40 45

    * - Kind
      - Required
      - Optional
    * - ``material``
      - ``m``, ``T``, ``p``, ``h``, ``e_PH``
      - ``e_T`` and ``e_M`` (required with ``split_physical_exergy``), ``e_CH``, or
        ``mass_composition`` or ``molar_composition`` (required with ``chemExLib`` when ``e_CH``
        is not given), ``x``, ``v``
    * - ``power``
      - ``energy_flow``
      -
    * - ``heat``
      -
      - ``energy_flow``
    * - ``other``
      -
      -

ExerPy computes the exergy of each connection itself, so values such as ``E`` in an exported
file are not needed.

The species of a ``mass_composition`` carry the names CoolProp knows, such as ``CH4``, ``N2`` or
``Ethane``. The chemical exergy of a mixture needs the molar mass of every species, so a species
CoolProp does not know stops the analysis with an error that names it.

*****
Units
*****

A value can be given in any unit. Write the unit next to it, under the same key with ``_unit``
added:

.. code-block:: json

    {"T": 15.0, "T_unit": "degC", "p": 1.013, "p_unit": "bar", "m": 36.0, "m_unit": "t / h"}

ExerPy converts every such value to SI before the analysis. A value without a unit is taken as SI.
The units are read with `pint <https://pint.readthedocs.io/>`__, so the usual names and symbols
work, for example ``degC``, ``bar``, ``kJ / kg``, ``kJ / kgK``, ``t / h``, ``kW``, ``MW`` or
``%``. The spellings of older ExerPy files, such as ``J / kgK``, ``m3 / s`` or ``-``, are read as
well. A unit that ExerPy does not know, or a unit of the wrong kind such as a pressure in ``K``,
stops the analysis with an error that names its place in the file.

These values are converted, wherever they appear in a component, its ``parameters`` or a
connection:

.. list-table::
    :header-rows: 1
    :widths: 60 40

    * - Value
      - SI unit
    * - ``T``, ``Tamb``, ``T_hot``, ``T_cold``
      - K
    * - ``p``, ``pamb``
      - Pa
    * - ``m``
      - kg/s
    * - ``n``
      - mol/s
    * - ``h``, ``e_PH``, ``e_T``, ``e_M``, ``e_CH``
      - J/kg
    * - ``s``
      - J/(kg K)
    * - ``energy_flow``, ``E``, ``E_PH``, ``E_T``, ``E_M``, ``E_CH``, ``Q``, ``P``, ``Q_Solar``
      - W
    * - ``kA``
      - W/K
    * - ``A``
      - m²
    * - ``v``, ``VM``
      - m³/s
    * - ``x``, ``eta_s``, ``eta_mech``, ``eta_el``, ``eta_cc``, ``lamb``
      - dimensionless

All other values keep the value and unit they have. Mass and molar fractions have no unit.

*********
Exporting
*********

:meth:`~exerpy.analyses.ExergyAnalysis.export_to_json` writes every value with its unit, in SI
unless asked otherwise. It adds the ``exergy_results`` of every component and the
``system_results`` of the plant. Pass ``units`` to write some values in other units:

.. code-block:: python

    ean.export_to_json("results.json", units={"T": "degC", "p": "bar", "E_D": "kW"})

``from_json`` reads such a file back in SI.

After an exergoeconomic analysis, the export of
:class:`~exerpy.analyses.ExergoeconomicAnalysis` writes the same file with the costs added:

.. code-block:: python

    eco = ExergoeconomicAnalysis(ean)
    eco.run(costs)
    eco.export_to_json("costs.json")

It holds the cost rates ``C_T``, ``C_M``, ``C_PH``, ``C_CH`` and ``C_TOT`` of every stream in
currency/h, the specific costs ``c_T`` to ``c_TOT`` in currency/GJ, the ``exergoeconomic_results``
of every component and the ``system_costs`` of the plant, again each with its unit.

**********
Validation
**********

``from_json`` checks the file before the analysis starts. The models parsed with ``from_tespy``,
``from_ebsilon`` and ``from_aspen`` are checked in the same way. The check has two steps:

1. **Structure**: missing values, values of the wrong type, unknown component types, two streams
   entering the same port, missing ``e_T`` and ``e_M`` when the physical exergy is split, and
   units that are unknown or of the wrong kind.
2. **Values**, once the structure is valid and the values are converted to SI: temperatures and
   pressures above zero, mass flows that are not negative, and mass and molar fractions between
   0 and 1.

ExerPy reports all problems of a step together, each with its place in the file:

.. code-block:: text

    Invalid ExerPy input (2 error(s)):
      - error: Expected a value >= 0, got -1.0 - at `$.connections['1'].m`
      - error: Expected a value > 0, got -10.0 - at `$.connections['2'].T`

The error is an :class:`~exerpy.schema.InputValidationError`, a ``ValueError`` whose ``issues``
attribute lists every problem. Some findings are only warnings and are logged, for example mass
fractions that do not add up to one or a connection that is not attached to any component. Pass
``validate=False`` to skip the check.

A file can also be checked without running an analysis, in the same order as ``from_json``:

.. code-block:: python

    import json

    from exerpy.schema import validate_structure
    from exerpy.schema import validate_values
    from exerpy.units import to_SI

    with open("my_model.json") as file:
        data = json.load(file)
    validate_structure(data)
    data, _ = to_SI(data)
    validate_values(data)

:func:`~exerpy.schema.validate` runs both steps at once, for a file that is already in SI.

A custom component declares the values it reads in a nested ``Input`` class, see
:class:`~exerpy.components.component.Component`. The check then covers it as well.

***********
JSON Schema
***********

:func:`~exerpy.schema.json_schema` returns the format as a `JSON Schema
<https://json-schema.org/>`__. Saved to a file, it lets an editor such as VS Code complete and
check a model while you write it. The schema describes the structure. The ranges of the values
are checked by ExerPy only.

.. code-block:: python

    import json

    from exerpy.schema import json_schema

    with open("exerpy_schema.json", "w") as file:
        json.dump(json_schema(), file, indent=4)
