"""Constrained scalar types of the input, for the msgspec structs that describe it.

ExerPy takes all values in SI units. The types are shared by the component ``Input``
structs and by :mod:`exerpy.schema`, and carry their bounds and descriptions into the
JSON Schema.
"""

from typing import Annotated

from msgspec import Meta

Name = Annotated[str, Meta(min_length=1)]
Temperature = Annotated[float, Meta(gt=0, description="Absolute temperature in K")]
Pressure = Annotated[float, Meta(gt=0, description="Absolute pressure in Pa")]
MassFlow = Annotated[float, Meta(ge=0, description="Mass flow in kg/s")]
Fraction = Annotated[float, Meta(ge=0, le=1)]
ConnectorIndex = Annotated[int, Meta(ge=0, description="0-based port index on the component")]
SpecificExergy = Annotated[float, Meta(description="Specific exergy in J/kg")]
Branches = Annotated[float, Meta(gt=0, description="Number of identical parallel branches")]
Composition = dict[str, Fraction]
