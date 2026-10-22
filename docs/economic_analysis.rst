.. _economic_analysis_label:

#################
Economic Analysis
#################

The economic analysis of ExerPy follows the **total revenue requirement (TRR) method** as presented by
Bejan, Tsatsaronis and Moran :cite:`Bejan1996`. The total revenue requirement of a plant is the money
that has to come in over a year to cover everything that owning and operating it costs in that year:
the recovery of the capital invested and the return on it, the operating and maintenance expenses,
and the fuel. Those three do not fall evenly over the life of a plant. The capital-related costs are
highest at the beginning and fall as the investment is written off, while the fuel and the maintenance
costs rise year after year with escalation. Comparing a single year of one design against a single
year of another would therefore compare two arbitrary points on two different curves.

The method removes that arbitrariness by **levelizing**: the uneven stream of yearly expenditures is
replaced by the constant yearly amount that has the same present value over the lifetime of the plant.
Two designs with quite different cost profiles over time then become directly comparable, and a single
levelized figure can be attached to each component.

.. dropdown:: Where this step fits: steps 3 and 4 of the workflow

    .. include:: /_workflow.rst

*************************************
What the cost rate of a component is
*************************************

An exergoeconomic analysis needs one number per component, its cost rate :math:`\dot{Z}_j`. It is the
share of the levelized yearly costs of the plant that belongs to component :math:`j`, expressed per
hour of operation, and it has two parts:

.. math::

    \dot{Z}_j = \dot{Z}^\mathrm{CC}_j + \dot{Z}^\mathrm{OM}_j

:math:`\dot{Z}^\mathrm{CC}_j` covers the **capital**: what it cost to buy the component, install it,
pipe it, wire it, engineer it and finance it, recovered over the lifetime of the plant.
:math:`\dot{Z}^\mathrm{OM}_j` covers **operating and maintenance**: what it costs to keep that
component running, service it and replace its wearing parts. Both are levelized, so
:math:`\dot{Z}_j` is not what the component costs in any particular year but the constant equivalent.

The unit is currency per hour, the same unit as the cost rates :math:`\dot{C}` that flow along the
streams of the plant, which is what lets the cost balance of a component be written as

.. math::

    \sum_\mathrm{out} \dot{C} = \sum_\mathrm{in} \dot{C} + \dot{Z}_j

In words: everything leaving a component carries the cost of everything entering it, plus what the
component itself costs to own and run. :math:`\dot{Z}_j` is the only place where money that did not
come in with a stream enters the analysis, and it is what makes an exergoeconomic result an economic
statement rather than a purely thermodynamic one. Weighed against the cost of the exergy a component
destroys, :math:`\dot{C}_\mathrm{D}`, it also answers the question the analysis exists to answer: is
this component expensive because it is inefficient, or because the equipment itself is costly?

The problem is that :math:`\dot{Z}_j` is almost never what an engineer has at hand. What is known is
what a piece of equipment costs to buy, and which year that price refers to.
:class:`~exerpy.analyses.EconomicAnalysis` closes that gap: it takes the purchased equipment costs
:math:`\mathrm{PEC}_j` and a handful of economic assumptions and returns the cost rates
:math:`\dot{Z}_j`.

*****************
Nomenclature
*****************

.. list-table:: Symbols and abbreviations
    :widths: 14 40 16
    :header-rows: 1
    :class: tight-table

    * - Symbol
      - Meaning
      - Unit
    * - :math:`\mathrm{PEC}`
      - Purchased equipment cost of a component, at the price level of its reference year
      - currency
    * - :math:`\mathrm{PEC}_\mathrm{base}`
      - Purchased equipment cost carried to the base year
      - currency
    * - :math:`y_\mathrm{ref}`
      - Reference year: the year whose price level a cost from a source, such as a manufacturer or
        the literature, is given in (``reference_year``)
      - a
    * - :math:`y_\mathrm{base}`
      - Base year of the analysis: the year every cost is carried to (``base_year``)
      - a
    * - :math:`\mathrm{FCI}`
      - Fixed capital investment: the direct and indirect costs of building the plant
      - currency
    * - :math:`\mathrm{TCI}`
      - Total capital investment: the fixed capital investment and the other outlays
      - currency
    * - :math:`f_\mathrm{TCI}`
      - Ratio of the total capital investment to the purchased equipment cost
      - \-
    * - :math:`\mathrm{CC}`
      - Carrying charges: the capital-related costs
      - currency/a
    * - :math:`\mathrm{OMC}`
      - Operating and maintenance costs
      - currency/a
    * - :math:`\mathrm{FC}`
      - Fuel costs, that is, the cost of the streams entering the plant
      - currency/a
    * - :math:`\mathrm{TRR}`
      - Total revenue requirement
      - currency/a
    * - :math:`\mathrm{CRF}`
      - Capital recovery factor
      - \-
    * - :math:`\mathrm{CELF}`
      - Constant escalation levelization factor
      - \-
    * - :math:`i_\mathrm{eff}`
      - Effective rate of return
      - 1/a
    * - :math:`r_\mathrm{n}`
      - Constant nominal escalation rate of a recurring expenditure
      - 1/a
    * - :math:`n`
      - Lifetime of the plant, the book life
      - a
    * - :math:`\tau`
      - Operating hours of the plant per year, the full-load hours
      - h/a
    * - :math:`I`
      - Plant cost index of a year
      - \-

A subscript :math:`\mathrm{L}` marks a levelized value, and a subscript :math:`j` a component. The
subscript :math:`\mathrm{ref}` marks a cost from a source and its year, such as the cost of a
reference component, and :math:`\mathrm{base}` the base year of the analysis.

.. _purchase_equipment_costs_label:

*********************************************
Where the purchased equipment costs come from
*********************************************

The analysis starts from the purchased equipment cost :math:`\mathrm{PEC}_j` of every component, in
the currency and the year :math:`y_{\mathrm{ref},j}` it refers to. ExerPy contains no cost data, so the costs come
from the user, in one of four ways or a mix of them, component by component. Each way below is
shown for one component; ``# ...`` marks what a real plant adds, such as its other components, and
``ean`` is the analysed plant, an :class:`~exerpy.analyses.ExergyAnalysis` after ``analyse()``.
:ref:`Purchased Equipment Costs from Four Sources <examples_purchase_costs_label>` shows all four on
one plant.

1. Known costs
==============

Costs taken from a source: a manufacturer, the literature or a built plant. Nothing is read from
the model; the cost is given with the year it refers to. The analysis escalates it to the
base year and turns it into the cost rate :math:`\dot{Z}` of the component:

.. code-block:: python

    from exerpy import EconomicAnalysis

    eco = EconomicAnalysis(
        PEC={
            "COMP": 300000.0,                    # EUR, from a source
            # ... the other components
        },
        reference_year={"COMP": 2021},           # the year of the source
        base_year=2025,                          # the year every cost is carried to
        cost_index={2021: 112.0, 2025: 143.0},   # placeholder values of a plant cost index
        i_eff=0.12, n=20, tau=6000, f_tci=4.5, omc_share=0.015,
    )
    eco.economic_results()                       # the cost rate of every component

The parameters of the analysis are explained in the sections below; :ref:`From Equipment Costs to the
Cost of the Product <examples_heatpump_exergoeconomic_label>` carries the cost rates on to the
exergoeconomic analysis.

.. _scaled_cost_label:

2. Scaled from a reference component
====================================

Where the cost of a reference component is known, from the literature or a manufacturer, say a heat
exchanger of a given area bought in a given year, the cost of a component of the same type and
a different size follows from it with an exponent:

.. math::

    \mathrm{PEC}_j = \mathrm{PEC}_{\mathrm{ref},j} \left(\frac{X_j}{X_{\mathrm{ref},j}}\right)^{\alpha_j}
    \cdot \frac{I_{y_\mathrm{base}}}{I_{y_{\mathrm{ref},j}}}

:math:`X` is the characteristic size the cost depends on, for example the heat transfer area of a
heat exchanger, the power of a machine or the volume of a vessel, :math:`\mathrm{PEC}_\mathrm{ref}`
and :math:`X_\mathrm{ref}` the cost and the size of the reference component,
and :math:`\alpha` the scaling exponent. Its default of 0.6 is the
six-tenths rule of cost estimation: doubling the size raises the cost by about 52 %, not 100 %,
because a larger unit needs proportionally less material, labour and engineering. The last factor
carries the cost of the reference component from the year it was paid, :math:`y_{\mathrm{ref},j}`, to the
base year of the analysis, :math:`y_\mathrm{base}`, with the plant cost index, like any other
cost of the analysis (:ref:`below <escalation_label>`).

The component gives the cost and the size of its reference instead of a cost. The year that cost
was paid is its ``reference_year``; the analysis carries it to ``base_year`` with the plant cost
index, which needs a value for both years. In the example, two heat exchangers of a combined cycle
are scaled by their area, with reference costs from 2023 and 2021 carried to 2025 (all costs and
index values are placeholders):

.. code-block:: python

    from exerpy import costing

    eco = EconomicAnalysis(
        PEC={
            # condenser: no U, so the default of its cell applies (shell-and-tube by default)
            "COND": {"PEC_ref": 2.0e6, "size_ref": 5000.0, "size_by": "area"},
            # economiser: a finned-tube bundle in the flue gas, with the U of the actual exchanger
            "ECO": {"PEC_ref": 1.5e6, "size_ref": 20000.0, "size_by": "area",
                    "exchanger_type": "finned_tube", "U": 40.0},
            # ... the other components
        },
        reference_year={"COND": 2023, "ECO": 2021},   # the year each reference cost was paid
        base_year=2025,                          # the year every cost is carried to
        cost_index={2021: 112.0, 2023: 133.0, 2025: 143.0},   # placeholder values, one per year used
        exergy_analysis=ean,                     # the areas are read from it
        # ... the parameters as in 1.
    )
    eco.economic_results()                       # also lists the reference, the size and the exponent

    # The coefficient each section of the condenser took, and where it comes from:
    for s in costing.heat_exchanger_sections(ean.components["COND"])["sections"]:
        print(s["hot"], s["cold"], s["U"], s["U_scope"], s["U_cell"])
    # two-phase liquid 3362.0 default C022

``size_by`` names the size the reference refers to, one of :func:`~exerpy.costing.quantities`, for
example ``"power"`` in W or ``"area"`` in m², and ``size_ref`` is given in the same SI unit. The size
of the component is then read automatically from the analysed plant, which is passed as
``exergy_analysis``, with :func:`~exerpy.costing.size`, see :ref:`Component Sizing
<component_sizing_label>`. An area also takes the ``exchanger_type`` and the coefficients ``U`` of
the exchanger. Without ``U``, every section takes the default of its comparable cell, as the
condenser does here; where a section has no cell, the analysis stops and asks for its ``U``. A size
the model does not determine, such as the volume of a vessel, is given directly as ``"size"`` in the
units of ``size_ref``, and ``"exponent"`` replaces the default of 0.6.
In a JSON file the same keys go into the entry of the component, next to ``reference_year``, ``f_tci``
and ``omc_share``, with ``U`` as one value for every section, and
:meth:`~exerpy.analyses.EconomicAnalysis.from_json` takes the exergy analysis the same way.
:meth:`~exerpy.analyses.EconomicAnalysis.economic_results` lists the scaled components with the cost
and size of their reference, their size and exponent and the resulting cost.

.. note::

    The rule holds for a component of the same type, material and pressure rating as the reference,
    and over a moderate range of sizes, typically up to a factor of ten. Beyond that, the
    larger unit often needs a different construction, or several units in parallel. The exponent
    differs between types of equipment, roughly 0.4 to 0.9; where a better value is known for the
    type, it belongs in ``exponent``.

3. User-defined cost equations
==============================

A Python function of one or more sizes of a component, for example from in-house data.
:func:`~exerpy.costing.sizes` reads the sizes from the model in SI units, see :ref:`Component Sizing
<component_sizing_label>`; the function and the year its costs refer to come from the user. The
equation below is fictitious and only shows the form:

.. code-block:: python

    from exerpy import costing

    def my_compressor_cost(power_kw, pressure_ratio):    # fictitious placeholder
        return 1200.0 * power_kw**0.8 * pressure_ratio**0.1

    s = costing.sizes(ean.components["COMP"])      # SI units: W, kg/s, m³/s, ...

    eco = EconomicAnalysis(
        PEC={
            "COMP": my_compressor_cost(s["power"] * 1e-3, s["pressure_ratio"]),
            # ... the other components
        },
        reference_year={"COMP": 2025},           # the year the equation refers to
        base_year=2025,                          # the same year, so no cost index is needed
        # ... the parameters as in 1.
    )
    eco.economic_results()

4. Correlations of OpenPyTEA
============================

The published cost correlations collected in `OpenPyTEA <https://github.com/pbtamarona/OpenPyTEA>`__
:cite:`Tamarona2026`, read at runtime (``pip install exerpy[costs]``).
:func:`~exerpy.costing.estimate` does the following automatically:

- it reads the size the correlation is based on from the model and converts it into the units of
  the correlation;
- it checks the size against the range of the correlation; outside it, it extrapolates from the
  nearest bound, or splits the component into parallel units with ``outside="parallel"``;
- for a heat exchanger, it takes the exchanger type the correlation describes.

The user gives:

- the correlation, by its key (:func:`~exerpy.costing.correlations` lists them, and
  :func:`~exerpy.costing.default_correlation` suggests one per component);
- for a heat exchanger, the coefficients ``U`` where no default cell applies, see
  :ref:`Component Sizing <component_sizing_label>`;
- for a correlation based on a size the model does not give, that size as ``value``;
- the conversion of the result into the currency of the analysis: the cost comes in US dollars of
  the year of the correlation, which :func:`~exerpy.costing.per_dollar` converts, and the plant cost
  index OpenPyTEA ships, :func:`~exerpy.costing.cost_index`, carries it to the base year.

.. code-block:: python

    from exerpy import costing

    cond_estimate = costing.estimate(ean.components["COND"], "plate_frame_hx_towler_2010", U=2000.0)
    print(cond_estimate["PEC"], cond_estimate["reference_year"], cond_estimate["fit"]["status"])

    eco = EconomicAnalysis(
        PEC={
            # the correlation, converted from USD to EUR at the year of the correlation
            "COND": cond_estimate["PEC"] * costing.per_dollar("EUR", cond_estimate["reference_year"]),
            "COMP": 300000.0,                    # a known cost from a source, in EUR
            # ... the other components
        },
        reference_year={
            "COND": cond_estimate["reference_year"],   # the year of the correlation, 2010
            "COMP": 2021,                        # the year of its source
        },
        cost_index=costing.cost_index(),         # one index carries both costs to the base year
        base_year=2025,
        # ... the parameters as in 1.
    )
    eco.economic_results()

The condenser is costed with a correlation and the compressor with a known cost from a source, so
the two costs come in different currencies and from different years. Only the cost from the
correlation is converted from US dollars; the known cost is already in euros. Each cost keeps its own reference year, 2010 and
2021, and one plant cost index carries both to the base year. Here it is the index OpenPyTEA ships,
which ends in 2024, so the last year is bridged with the escalation rate :math:`r_\mathrm{n}`, with a
warning saying so.

.. _pec_together_label:

Putting the sources together
============================

The entries of the four ways go into one ``PEC`` and one ``reference_year``, component by component. The
analysed plant is passed as ``exergy_analysis`` where a scaled cost reads its size from it:

.. code-block:: python

    eco = EconomicAnalysis(
        PEC={"COMP": 300000.0, "COND": {"PEC_ref": 90000.0, "size_ref": 50.0, "size_by": "area", "U": 2000.0}},
        reference_year={"COMP": 2021, "COND": 2023},
        base_year=2025,
        cost_index={2021: 112.0, 2023: 133.0, 2025: 143.0},
        exergy_analysis=ean,
        i_eff=0.12, n=20, tau=6000, f_tci=4.5, omc_share=0.015,
    )

A cost from a year :math:`y_{\mathrm{ref},j}` other than the base year :math:`y_\mathrm{base}` is escalated with
the plant cost index :math:`I`, see :ref:`below <escalation_label>`; a cost in another currency is
converted first, for the US dollar with :func:`~exerpy.costing.per_dollar`.

*****************************
The capital investment
*****************************

The purchased equipment cost :math:`\mathrm{PEC}_j` is the cost of the bare component. It is a
fraction of what the plant
costs to build: the equipment has to be installed, piped, instrumented and wired, the project has to
be engineered and supervised, and the plant needs a contingency, start-up costs and working capital.
Following the factor method, all of that is expressed as a multiple of the purchased equipment cost,
the total capital investment :math:`\mathrm{TCI}_j` with the installation factor
:math:`f_{\mathrm{TCI},j}`:

.. math::

    \mathrm{TCI}_j = f_{\mathrm{TCI},j} \cdot \mathrm{PEC}_j

The factor is given once for the whole plant or separately per component, for example where the
installation effort differs between kinds of equipment.

.. _escalation_label:

Escalating a cost to the base year
=======================================

Costs from different years cannot be added. A cost from the past is carried forward from its
reference year :math:`y_{\mathrm{ref},j}` to the base year :math:`y_\mathrm{base}` with a plant cost index :math:`I`, whose
values are an input of the analysis, and into the future with the nominal escalation rate
:math:`r_\mathrm{n}`:

.. math::

    \mathrm{PEC}_{\mathrm{base},j} = \mathrm{PEC}_j \cdot \frac{I_{y_\mathrm{base}}}{I_{y_{\mathrm{ref},j}}}

An index reaches only as far as the years that have passed, so the base year, or a recent cost,
may lie beyond its last entry; an old cost may lie before its first. The index is used for the years it
covers and the nominal escalation rate bridges every year outside of it, forward or backward:

.. math::

    \mathrm{PEC}_{\mathrm{base},j} = \mathrm{PEC}_j \cdot \frac{I_{\bar{y}_\mathrm{base}}}{I_{\bar{y}_{\mathrm{ref},j}}}
    \cdot \left(1 + r_\mathrm{n}\right)^{(\bar{y}_{\mathrm{ref},j} - y_{\mathrm{ref},j}) + (y_\mathrm{base} - \bar{y}_\mathrm{base})}

where :math:`\bar{y}` is a year clamped to the range of the index. A cost given in the base year
needs no index at all; without any index the rate alone carries the costs. Both cases are reported in a
warning. Only a year inside the range of the index that has no value is an error, since no rate can
stand in for a published value.

*****************************
Levelizing
*****************************

The capital recovery factor :math:`\mathrm{CRF}` turns a single investment into the equal yearly
payment that repays it over the lifetime :math:`n` of the plant at the effective rate of return
:math:`i_\mathrm{eff}`:

.. math::

    \mathrm{CRF} = \frac{i_\mathrm{eff}\,(1 + i_\mathrm{eff})^{n}}{(1 + i_\mathrm{eff})^{n} - 1}

An expenditure that repeats every year and escalates at a constant nominal rate is not an equal
payment, so it is levelized with the constant escalation levelization factor, which relates the value
of the expenditure at the beginning of the first year, :math:`P_0`, to the equal yearly payment
:math:`A` that replaces it:

.. math::

    \mathrm{CELF} = \frac{A}{P_0}
    = \frac{k\,\left(1 - k^{n}\right)}{1 - k} \cdot \mathrm{CRF}
    \qquad
    k = \frac{1 + r_\mathrm{n}}{1 + i_\mathrm{eff}}

.. important::

    The cost handed to the analysis is :math:`P_0`, the value at the beginning of the first year, at
    the price level of the base year. The expenditure of the first year of operation is
    :math:`P_0 \cdot (1 + r_\mathrm{n})`, so a first-year figure has to be divided by
    :math:`(1 + r_\mathrm{n})` before it is used here.

The levelized carrying charges and the levelized operating and maintenance cost follow:

.. math::

    \mathrm{CC}_\mathrm{L} = \mathrm{TCI} \cdot \mathrm{CRF}
    \qquad
    \mathrm{OMC}_\mathrm{L} = \mathrm{CELF}(r_\mathrm{n}) \cdot \sum_j \mathrm{OMC}_{0,j}

The first-year operating and maintenance cost :math:`\mathrm{OMC}_{0,j}` of a component is a share
:math:`\mathrm{omc}_j` of its purchased equipment cost or of its total capital investment, whichever
:code:`omc_basis` names. The two differ by the installation factor :math:`f_{\mathrm{TCI},j}`, so a
share meant for one basis is badly wrong on the other:

.. math::

    \mathrm{OMC}_{0,j} = \mathrm{omc}_j \cdot \mathrm{PEC}_{\mathrm{base},j}
    \qquad \text{or} \qquad
    \mathrm{OMC}_{0,j} = \mathrm{omc}_j \cdot \mathrm{TCI}_j

*****************************
The cost rate of a component
*****************************

Each component carries its own investment and its own operating cost, spread over the operating hours
:math:`\tau` of the year:

.. math::

    \dot{Z}^\mathrm{CC}_j = \frac{f_{\mathrm{TCI},j} \cdot \mathrm{PEC}_{\mathrm{base},j}
    \cdot \mathrm{CRF}}{\tau}
    \qquad
    \dot{Z}^\mathrm{OM}_j = \frac{\mathrm{OMC}_{0,j} \cdot \mathrm{CELF}}{\tau}
    \qquad
    \dot{Z}_j = \dot{Z}^\mathrm{CC}_j + \dot{Z}^\mathrm{OM}_j

Where the factors are given once for the whole plant, this is the same as levelizing the plant and
sharing the result out among the components in proportion to their purchased equipment cost.

*****************************
The cost of the fuel
*****************************

The streams entering the plant are bought over its whole lifetime and escalate at their own rates, so
their cost is levelized in the same way:

.. math::

    c_{\mathrm{L},i} = c_{0,i} \cdot \mathrm{CELF}(r_{\mathrm{n},i})

That levelized specific cost, not the price of the first year, is what the exergoeconomic analysis is
given. Levelizing the fuel and the investment over the same lifetime is what makes the resulting cost
of the product a levelized cost as well.

A cost may be given per unit of exergy or per unit of energy. A price given on a heating value basis, for
example a gas price in currency per MWh, is an energy-based cost and is converted with the ratio of
the energy flow to the exergy flow of that stream.

The levelized total revenue requirement of the plant is the sum of the three:

.. math::

    \mathrm{TRR}_\mathrm{L} = \mathrm{CC}_\mathrm{L} + \mathrm{OMC}_\mathrm{L}
    + \mathrm{FC}_\mathrm{L}

*****************************
Using the class
*****************************

Four inputs have no meaningful default and are required: the purchased equipment costs
:math:`\mathrm{PEC}_j` (``PEC``), the effective rate of return :math:`i_\mathrm{eff}` (``i_eff``), the
lifetime of the plant :math:`n` (``n``) and its operating hours :math:`\tau` (``tau``). The
installation factor :math:`f_\mathrm{TCI}` (``f_tci``) and the maintenance share :math:`\mathrm{omc}`
(``omc_share``) are required too, since neither can be defaulted without silently changing the
result. Each of the two takes one value for the whole plant or one per component.

The other inputs are optional: the reference year :math:`y_{\mathrm{ref},j}` (``reference_year``), the base year
:math:`y_\mathrm{base}` (``base_year``) and the plant cost index :math:`I` (``cost_index``) for
costs from different years, the nominal escalation rate :math:`r_\mathrm{n}` (``r_n``, 0.05 by
default), the costs :math:`c_0` of the streams entering the plant (``fuel_costs``), the basis of the
maintenance share (``omc_basis``) and the currency (``currency``).

.. code-block:: python

    from exerpy import EconomicAnalysis

    eco = EconomicAnalysis(
        PEC={"COMP": 300000.0, "COND": 120000.0},
        i_eff=0.12,
        n=20,
        tau=6000,
        f_tci=4.16,
        omc_share=0.03,
        omc_basis="TCI",
    )
    costs = eco.compute_z()

From a file
===========

The same assumptions can be read from a JSON file with
:meth:`~exerpy.analyses.EconomicAnalysis.from_json`. The file keeps everything about one component in
one entry, so its cost, its reference year and the factors that belong to it cannot drift
apart:

.. code-block:: json

    {
        "i_eff": 0.12,
        "n": 20,
        "tau": 6000,
        "currency": "EUR",
        "r_n": 0.05,

        "base_year": 2025,
        "cost_index": {"2021": 112.0, "2024": 139.0, "2025": 143.0},

        "f_tci": 4.5,
        "omc_share": 0.015,
        "omc_basis": "PEC",

        "components": {
            "COMP": {"PEC": 300000.0, "reference_year": 2021, "f_tci": 4.2, "omc_share": 0.03},
            "COND": {"PEC": 120000.0, "reference_year": 2024, "f_tci": 6.3},
            "VAL": 5000.0
        },

        "fuel_costs": {
            "e1": {"c": 30.0, "r_n": 0.04},
            "11": 0.0
        }
    }

.. code-block:: python

    eco = EconomicAnalysis.from_json("costs.json")

A value given at the top level applies to the whole plant, and a component that names the same key
overrides it, so only what differs has to be written out. In the file above :code:`COND` takes the
plant-wide maintenance share :math:`\mathrm{omc} = 0.015` and :code:`VAL` takes both the plant-wide
installation factor :math:`f_\mathrm{TCI} = 4.5` and that share. A component may be a plain number instead of an object, and so may an entry of
:code:`fuel_costs`; both are then read as the cost with everything else left at its default.

Where every component shares the same assumptions, the file collapses to a list of costs: leave out
:code:`reference_year`, :code:`base_year` and :code:`cost_index`, and nothing is escalated.

Getting the costs out
=====================

:meth:`~exerpy.analyses.EconomicAnalysis.compute_costs` returns the cost rates of the components and
the levelized costs of the entering streams together, keyed the way
:meth:`~exerpy.analyses.ExergoeconomicAnalysis.run` expects them, and checks both against the plant:
a component without an equipment cost, a cost for something that is not in the plant, a cost for a
component that carries no cost balance and a stream entering the plant without a cost are all
reported instead of silently changing the result.
:meth:`~exerpy.analyses.EconomicAnalysis.compute_z` and
:meth:`~exerpy.analyses.EconomicAnalysis.compute_c` return the two halves on their own, and
:meth:`~exerpy.analyses.EconomicAnalysis.economic_results` prints the levelized costs of the plant
and the cost rate of every component.

.. code-block:: python

    from exerpy import ExergoeconomicAnalysis

    eco.economic_results(ean)

    exergoeco = ExergoeconomicAnalysis(ean, currency="EUR")
    exergoeco.run(eco.compute_costs(ean))

The worked example is
:ref:`From Equipment Costs to the Cost of the Product <examples_heatpump_exergoeconomic_label>`.

.. note::

    The method covers the capital, operating and fuel costs. It does not resolve the financing of the
    investment into debt, preferred stock and common equity, and it carries no income taxes or
    insurance; those enter the year-by-year analysis of the reference and are absorbed here into the
    effective rate of return and the installation factor.
