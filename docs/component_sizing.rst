.. _component_sizing_label:

################
Component Sizing
################

The economic analysis needs the purchased equipment cost :math:`\mathrm{PEC}_j` of every component.
Where that cost is known, for example from a manufacturer, no size is needed. Where it is estimated
from the size of the component, by :ref:`scaling the cost of a reference component
<scaled_cost_label>`, with a user-defined cost equation or with a correlation of OpenPyTEA
:cite:`Tamarona2026`, sizing means reading that size from the model.

.. dropdown:: Where this step fits: step 2 of the workflow

    .. include:: /_workflow.rst

What a cost function captures
=============================

What a component costs depends on far more than its size: the pressure and the temperature it is
designed for, which set wall thicknesses and the grade of the material; the material the fluid
requires; the construction type; the speed and the number of stages of a machine and the efficiency
it is built for; fouling allowances, standards, the site and the market. Cost estimation methods
capture these influences in different ways. In the factor methods introduced by Guthrie
:cite:`Guthrie1969,Guthrie1974` and developed further by Ulrich :cite:`Ulrich1984`, the cost of a
base design, usually carbon steel at moderate pressure, follows from one or more size parameters and
is multiplied by factors for the pressure, the material and the type of construction. Other cost
functions take thermodynamic variables directly, such as the pressure ratio and the isentropic
efficiency of a compressor or the inlet temperature of a turbine :cite:`Valero1994,Bejan1996`, and
the handbooks tabulate further correction factors :cite:`Towler2013`. ExerPy applies none of these
factors itself: they belong in a user-defined cost equation or in the choice of the correlation.

Which sizes a cost function takes
=================================

Which parameter a component is sized by depends on the cost function, not on the component. The
table gives examples; a cost function may take another size of the same component, or several.

.. list-table::
    :header-rows: 1
    :widths: 22 40 38

    * - Component
      - Size parameters of cost functions (examples)
      - Read from the model by :func:`~exerpy.costing.sizes`
    * - Compressor, fan, pump
      - shaft or driver power, inlet volume flow, mass flow, pressure ratio, head
      - ``power``, ``mass_flow``, ``volume_flow`` (inlet), ``pressure_ratio``
    * - Turbine
      - power, inlet or outlet volume flow, mass flow, inlet temperature
      - ``power``, ``mass_flow``, ``volume_flow`` (inlet), ``pressure_ratio``
    * - Motor, generator
      - power, speed, voltage
      - ``power``
    * - Heat exchanger
      - heat transfer area, heat flow, :math:`UA`, number of plates or shells
      - ``heat``, ``kA``, ``dT_lm``, ``area`` (see below)
    * - Steam generator
      - heat flow, steam mass flow
      - ``heat``, ``mass_flow`` (live steam)
    * - Simple heat exchanger
      - heat flow
      - ``heat``
    * - Drum, deaerator, flash tank, storage
      - volume, diameter, shell mass
      - none (they need residence times and a mechanical design)

:func:`~exerpy.costing.sizes` returns every size of the last column that the model determines, in SI units
(W, kg/s, m³/s, m², W/K, K, see :data:`~exerpy.costing.UNITS`), and :func:`~exerpy.costing.size`
returns one of them:

.. code-block:: python

    from exerpy import costing

    costing.sizes(ean.components["COMP"])
    # {"power": 894071.2, "mass_flow": 11.06, "volume_flow": 3.42, "pressure_ratio": 41.82}
    costing.size(ean.components["COND"], "heat")
    # 2105685.2

Each way of obtaining the purchased equipment cost takes them as it needs:

- **User-defined cost equations** take any of them, one or several, for example
  ``my_compressor_cost(s["volume_flow"], s["pressure_ratio"])`` with ``s = costing.sizes(comp)``.
- **Scaling from a reference** names the size the cost of the reference refers to with ``size_by``,
  for example ``"power"`` or ``"area"``, see :ref:`Scaling the cost of a reference component
  <scaled_cost_label>`.
- **OpenPyTEA**: :func:`~exerpy.costing.estimate` takes the size that has the dimension of the
  units of the chosen correlation, a power or a heat flow, an area, a volume flow at the inlet or a mass
  flow, and converts it into those units, the volume flow of a fan into ACFM for instance. A
  correlation based on a size the model does not give, such as the volume of a vessel or a product of two
  sizes like the flow times the square root of the head of a pump, takes the size given by hand as
  ``value``.

The area is the one size that needs more than the model: the overall heat transfer coefficient
:math:`U`. The rest of this page is about it.

The area of a heat exchanger
============================

The exchanger is taken as counter-flow and cut into sections at every point where one of its streams
crosses a saturation line. Every section then has one phase on each side, and its area follows from
the heat it transfers :math:`\dot{Q}_i`, its logarithmic mean temperature difference
:math:`\Delta T_{\mathrm{lm},i}` and its overall heat transfer coefficient :math:`U_i`:

.. math::

    A = \sum_i \frac{\dot{Q}_i}{U_i \, \Delta T_{\mathrm{lm},i}}

A condenser of a heat pump, for instance, has three sections: desuperheating (gas to liquid),
condensing (two-phase to liquid) and subcooling (liquid to liquid), each with its own coefficient.

The phase of a stream
---------------------

A stream is placed in one of four phases: *liquid*, *two-phase*, *gas* and *supercritical*. The
export of a simulation gives the state of a stream where it enters and where it leaves the
exchanger, not where it crosses a saturation line in between. For a stream of a single fluid, ExerPy
therefore takes the saturation states at its pressure from CoolProp :cite:`Bell2014` and follows the
stream through them; above its critical pressure the stream is supercritical. Only temperatures,
pressures, vapour qualities and enthalpy differences of the export enter, so the sections are the
same for TESPy, Ebsilon Professional and Aspen Plus models, whatever enthalpy reference the
simulator uses. A mixture, such as a flue gas, or a fluid CoolProp does not know is taken as
single-phase, with a temperature linear in the heat transferred: as a gas when its specific volume
is above 0.01 m³/kg and as a liquid otherwise, or by its fluid group where the export has no volume
flow.

Without sections
----------------

Where the sections cannot be formed (a temperature cross, a saturated end with an unknown quality,
a stream whose phase is unknown), or with ``method="kA"``, the area is :math:`A = kA / U` with the
heat transfer capacity :math:`kA` of the simulation. This needs a single coefficient :math:`U` from
the user; without one the area stays empty.

The overall heat transfer coefficient
=====================================

The coefficients of the actual exchanger, from a manufacturer, a design calculation or
measurements, are always the better basis; give them as ``U``. The defaults of ExerPy are a fallback
for a first estimate. For every section ExerPy takes the first of:

1. **your value**: one :math:`U` for every section, or one per section by its pair of phases, the
   phase of the hot stream first and that of the cold stream second, e.g. for a refrigerant that is
   desuperheated, condensed and subcooled by liquid water
   ``U={("gas", "liquid"): 500.0, ("two-phase", "liquid"): 2500.0, ("liquid", "liquid"): 1500.0}``;
   a pair the dictionary does not name goes on to the next step;
2. **the default of its comparable cell**: the published values for the same exchanger type, with
   the same fluid group and phase of the hot and of the cold stream, for example condensing steam
   on liquid water in a shell-and-tube exchanger;
3. otherwise an error that names the fluids and phases of the section and asks for its value.

No coefficient is taken from another fluid or another exchanger type. Every section reports the
coefficient it used and its scope (``"user"`` or ``"default"``), and for a default its cell, its
sources and their number. A default that rests on fewer than three independent sources is reported
as a warning.

.. _sizing_what_to_give_label:

What to give
------------

The phases, the fluid groups, the heat flows and the temperatures of the sections are read from the
model. The user gives at most three arguments, the same in :func:`~exerpy.costing.size`,
:func:`~exerpy.costing.sizes`, :func:`~exerpy.costing.heat_exchanger_area` and
:func:`~exerpy.costing.estimate`, and in a :ref:`scaled cost <scaled_cost_label>` of the economic
analysis:

.. list-table:: The arguments of the area of a heat exchanger
    :widths: 18 52 30
    :header-rows: 1
    :class: tight-table

    * - Argument
      - Values
      - Default
    * - ``exchanger_type``
      - a key of :data:`~exerpy.costing.EXCHANGER_TYPES`, see :ref:`below <sizing_exchanger_type_label>`
      - ``"shell_and_tube"``; for :func:`~exerpy.costing.estimate` the type of the correlation
    * - ``U``
      - nothing; one value in W/(m² K) for every section; or one per section as
        ``{(hot phase, cold phase): value}``, with the phases ``"liquid"``, ``"two-phase"``, ``"gas"``
        and ``"supercritical"``
      - every section takes the default of its comparable cell
    * - ``method``
      - ``"sections"``, or ``"kA"`` for :math:`A = kA / U` with one value of ``U``
      - ``"sections"``

In the combined cycle of the examples, flue gas evaporates water in the evaporator ``EVA`` and
superheats the steam in the superheater ``SH``. Neither the fluids nor the sections nor any
coefficient are given: ExerPy finds the sections, the phases and the fluid groups (flue gas on
water/steam) in the model and takes every coefficient from its cell. Only the exchanger type is
given, since the default, shell-and-tube, has no cell for flue gas:

.. code-block:: python

    from exerpy import ExergyAnalysis, costing

    ean = ExergyAnalysis.from_json("ccpp_tespy.json")   # any model: TESPy, Ebsilon, Aspen or JSON

    costing.size(ean.components["EVA"], "area", exchanger_type="finned_tube")   # 51318.8 m²
    costing.size(ean.components["SH"], "area", exchanger_type="finned_tube")    # 10299.4 m²

    # the sections ExerPy found, the coefficient each took and where it comes from
    for name in ("EVA", "SH"):
        sections = costing.heat_exchanger_sections(ean.components[name], exchanger_type="finned_tube")
        for s in sections["sections"]:
            print(name, s["hot"], s["cold"], s["U"], s["U_scope"], s["U_cell"])
    # EVA gas two-phase 42.0 default C038
    # EVA gas liquid 52.8 default C037
    # SH gas gas 61.7 default C036
    # SH gas two-phase 42.0 default C038

The evaporator has a short liquid section before the water boils, and the superheater a short
two-phase section before the steam is dry; each section takes the coefficient of its own pair of
phases. The cells of finned tubes rest on one source, so the calls also warn. A condenser of steam on
cooling water, ``COND``, needs no argument at all, since shell-and-tube is the default:
``costing.size(ean.components["COND"], "area")`` gives 1872.6 m² with the coefficient of cell C022.

Where no cell fits, the call stops and names what is missing. The condenser of the heat pump,
refrigerant on water, has no cell, so its coefficients are given per section:

.. code-block:: python

    costing.size(hp.components["COND"], "area")
    # ValueError: COND: no comparable cell for HFC/HFO (gas) to water/steam (liquid) in a
    # shell_and_tube exchanger; give it as U={('gas', 'liquid'): value} in W/m²K.

    # (hot phase, cold phase): the refrigerant is the hot stream, the water the cold one
    U = {("gas", "liquid"): 500.0, ("two-phase", "liquid"): 2500.0, ("liquid", "liquid"): 1500.0}
    costing.size(hp.components["COND"], "area", exchanger_type="plate", U=U)      # 71.7 m²

All possible values are listed on this page: the exchanger types and how a correlation of OpenPyTEA
maps to them :ref:`below <sizing_exchanger_type_label>`, the fluid groups after them, and every cell
with its default, range and sources in :ref:`the tables at the end <sizing_values_label>`. In code,
:data:`~exerpy.costing.EXCHANGER_TYPES` holds the types and :data:`~exerpy.costing.U_CELLS` the cells.

.. _sizing_exchanger_type_label:

The exchanger type
------------------

A comparable cell is found by three things: the exchanger type, the fluid groups and the phases of
the section. The area the coefficient refers to has to match the cost function as well.

The exchanger type is given as ``exchanger_type``, a key of :data:`~exerpy.costing.EXCHANGER_TYPES`,
shell-and-tube by default: ``shell_and_tube``, ``plate``, ``plate_fin``, ``finned_tube`` (steel finned
tubes of boilers and heat recovery steam generators), ``finned_coil`` (finned air coils, for example
of air source heat pumps and dry coolers), ``bare_tube_bundle``, ``air_cooled`` (fin-fan),
``double_pipe``, ``printed_circuit``, ``surface_condenser`` and ``other``. A heat exchanger costed
with an OpenPyTEA correlation takes the type of construction of that correlation, read from its
``type`` text; ``exchanger_type`` given to :func:`~exerpy.costing.estimate` overrides it.

.. csv-table:: The exchanger type ExerPy uses for an OpenPyTEA correlation
    :header: "The type of the OpenPyTEA correlation contains", "ExerPy takes the defaults of"
    :widths: 50 50

    "air (air cooler, air-cooled fin-fan)", "``air_cooled``"
    "pipe (double pipe, multiple pipe)", "``double_pipe``"
    "spiral (spiral plate, spiral tube)", "``other``"
    "plate & fin", "``plate_fin``"
    "plate (plate & frame, flat plate)", "``plate``"
    "anything else (shell & tube, U-tube, kettle, ...)", "``shell_and_tube``"

The fluid groups
----------------

The fluid group of a stream is recognized from its mass composition: water/steam, air, flue gas,
natural gas (methane), hydrogen, CO2, ammonia, ammonia-water (absorption), HFC/HFO (the refrigerants
named R...), hydrocarbon refrigerants (propane, butanes, pentanes, propylene, ...), siloxanes,
toluene/aromatics, thermal oil, molten salt and glycol/brine. A mixture of nitrogen and oxygen is
air; one that also carries combustion CO2 is flue gas; one of mostly methane is natural gas.

The area basis
--------------

A coefficient refers to a particular area, and a cost correlation is based on a particular area as
well. The two have to match: a coefficient based on the total finned area used with a correlation
based on the bare-tube area misprices the exchanger by the fin ratio, a factor of 10 to 20. The
tables below state the area basis of every cell; where a source does not state it, the tube outside
area is assumed for tubular exchangers.

Where the default values come from
==================================

276 published overall heat transfer coefficients were collected: from the handbooks of Perry
:cite:`Perry2008`, Towler and Sinnott :cite:`Towler2013` and the VDI Heat Atlas
:cite:`Roetzel2010,MuellerSteinhagen2010`, the worked examples of Ganapathy for boilers and heat
recovery steam generators :cite:`Ganapathy2003`, and studies of heat pumps, organic Rankine cycles,
feedwater heaters, condensers, concentrated solar power plants and supercritical CO2 cycles. 108 of
them form the 59 cells ExerPy uses; the others fit no cell, such as generic or refinery fluids, or
rest on weaker evidence, such as secondary citations or model assumptions. Only values of the same
cell are combined:

- **A cell** holds the values for one exchanger type and construction (a brazed chevron plate is not
  a flat-channel plate, a heat recovery steam generator bundle is not an air coil), one fluid group
  and phase of the hot and of the cold stream, and one area basis. It holds values of one zone of an
  exchanger, such as the condensing zone; averages over a whole exchanger with several zones are
  kept apart and not used as defaults.
- **The default** of a cell is the median of its values. A value is the one a source reports, the
  midpoint of a range it reports, or the median of the values it tabulates for one design. The
  tables give the range of the published values as well, and the number of independent sources: the
  same study, design or laboratory counts once, and a value one source took from another does not
  count again.
- **Where two cells** share the exchanger type, the phases and the fluid groups but differ in
  construction or area basis, one of them is the default: the one with more independent sources; on
  a tie, the one with more values; then the one with a stated area basis. For superheated steam on
  feedwater in a shell-and-tube exchanger, Shah et al. :cite:`Shah2019` give two coefficients:
  610 W/(m² K) for the baffled desuperheating zone and 261 W/(m² K) for steam that is still
  superheated when it reaches the unbaffled condensing zone. Both match a gas-to-liquid section of a
  shell-and-tube exchanger; the desuperheating zone is the default, since the other describes a
  special flow situation.

**Coverage.** Water and steam are covered best; three cells rest on three or more independent
sources, all of them water and steam. Most other cells rest on one source. HFC/HFO and hydrocarbon
refrigerants, CO2 below its critical pressure, siloxanes and air coils of heat pumps have few cells or
none, so the condensers and evaporators of heat pumps and organic Rankine cycles mostly need their
own ``U``.

.. warning::

    Even within one cell the published coefficients spread widely: condensing steam on water in a
    shell-and-tube exchanger ranges from 1000 to 5678 W/(m² K), depending on the velocities, the
    geometry, the tube material and the fouling allowance. A default gives a first estimate of the
    area and so of the purchased equipment cost; a design takes the coefficients of the actual
    exchanger.

.. _sizing_values_label:

The values
==========

The tables are generated from ``src/exerpy/data/heat_transfer_coefficients.json``, the file the
analysis reads, so they always show the values in use.

.. include:: _generated/heat_transfer_coefficients.rst

.. seealso::

    :ref:`Purchased Equipment Costs from Four Sources <examples_purchase_costs_label>` sizes the
    components of a heat pump and obtains their purchased equipment costs in four ways.
