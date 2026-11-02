"""Scalar types of the input, for the msgspec structs that describe it.

The types are shared by the component ``Input`` structs and by :mod:`exerpy.schema`.
Their description goes into the JSON Schema. Their :class:`Limit` is the range of a
reasonable value in SI units. It is checked by :func:`exerpy.schema.check_values`, not
while the structure of the input is read.
"""

from dataclasses import dataclass
from typing import Annotated

from msgspec import Meta


@dataclass(frozen=True)
class Limit:
    """Range of a reasonable value, in SI units."""

    gt: float | None = None
    ge: float | None = None
    le: float | None = None

    def violation(self, value: float) -> str | None:
        """Return the bound ``value`` breaks, e.g. ``"> 0"``, or ``None``."""
        if self.gt is not None and not value > self.gt:
            return f"> {self.gt:g}"
        if self.ge is not None and not value >= self.ge:
            return f">= {self.ge:g}"
        if self.le is not None and not value <= self.le:
            return f"<= {self.le:g}"
        return None


Name = Annotated[str, Meta(min_length=1)]
Temperature = Annotated[float, Meta(description="Absolute temperature in K"), Limit(gt=0)]
Pressure = Annotated[float, Meta(description="Absolute pressure in Pa"), Limit(gt=0)]
MassFlow = Annotated[float, Meta(description="Mass flow in kg/s"), Limit(ge=0)]
Fraction = Annotated[float, Meta(description="Mass or molar fraction"), Limit(ge=0, le=1)]
ConnectorIndex = Annotated[int, Meta(ge=0, description="0-based port index on the component")]
SpecificExergy = Annotated[float, Meta(description="Specific exergy in J/kg")]
Branches = Annotated[float, Meta(description="Number of identical parallel branches"), Limit(gt=0)]
Composition = dict[str, Fraction]
