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
year of another would therefore compare two arbitrary points of two different curves.

The method removes that arbitrariness by **levelizing**: the uneven stream of yearly expenditures is
replaced by the constant yearly amount that has the same present value over the lifetime of the plant.
Two designs with quite different cost profiles over time then become directly comparable, and a single
levelized figure can be attached to each component.

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
what a piece of equipment costs to buy, and in which year that price was quoted.
:class:`~exerpy.analyses.EconomicAnalysis` closes that gap: it takes the purchase equipment costs and
a handful of economic assumptions and returns the cost rates.

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
      - Purchase equipment cost of a component
      - currency
    * - :math:`\mathrm{FCI}`
      - Fixed capital investment: the direct and indirect costs of building the plant
      - currency
    * - :math:`\mathrm{TCI}`
      - Total capital investment: the fixed capital investment and the other outlays
      - currency
    * - :math:`f_\mathrm{TCI}`
      - Ratio of the total capital investment to the purchase equipment cost
      - \-
    * - :math:`\mathrm{CC}`
      - Carrying charges: the capital-related costs
      - currency/a
    * - :math:`\mathrm{OMC}`
      - Operating and maintenance costs
      - currency/a
    * - :math:`\mathrm{FC}`
      - Fuel costs, that is the cost of the streams entering the plant
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
      - Operating hours of the plant per year, the full load hours
      - h/a
    * - :math:`I`
      - Plant cost index of a year
      - \-

A subscript :math:`\mathrm{L}` marks a levelized value, and a subscript :math:`j` a component.

*****************************
The capital investment
*****************************

The purchase equipment cost is the cost of the bare components. It is a fraction of what the plant
costs to build: the equipment has to be installed, piped, instrumented and wired, the project has to
be engineered and supervised, and the plant needs a contingency, a start-up and working capital.
Following the factor method, all of that is expressed as a multiple of the purchase equipment cost:

.. math::

    \mathrm{TCI}_j = f_{\mathrm{TCI},j} \cdot \mathrm{PEC}_j

The factor is given once for the whole plant or separately per component. Per component is the more
honest choice wherever the equipment differs in kind: the installation effort of a heat exchanger is
not that of an electric motor, and a single factor for a plant with much small electrical equipment
overstates the investment.

Escalating a cost to the reference year
=======================================

Costs from different years cannot be added. A cost from the past is carried forward with a plant cost
index, whose values are an input of the analysis, and a cost into the future with an escalation rate:

.. math::

    \mathrm{PEC}_{\mathrm{ref},j} = \mathrm{PEC}_j \cdot \frac{I_\mathrm{ref}}{I_{y(j)}}

An index reaches only as far as the years that have passed, so the reference year may lie beyond its
last entry. The cost is then carried with the index as far as it reaches and the remaining years are
bridged with the nominal escalation rate:

.. math::

    \mathrm{PEC}_{\mathrm{ref},j} = \mathrm{PEC}_j \cdot \frac{I_{y_\mathrm{last}}}{I_{y(j)}}
    \cdot \left(1 + r_\mathrm{n}\right)^{y_\mathrm{ref} - y_\mathrm{last}}

and says in a warning that it did so.

*****************************
Levelizing
*****************************

The capital recovery factor turns a single investment into the equal yearly payment that repays it
over the lifetime of the plant:

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

    The cost handed to the analysis is :math:`P_0`, the value at the beginning of the first year, in
    the price level of the reference year. The expenditure of the first year of operation is
    :math:`P_0 \cdot (1 + r_\mathrm{n})`, so a first-year figure has to be divided by
    :math:`(1 + r_\mathrm{n})` before it is used here.

The levelized carrying charges and the levelized operating and maintenance cost follow:

.. math::

    \mathrm{CC}_\mathrm{L} = \mathrm{TCI} \cdot \mathrm{CRF}
    \qquad
    \mathrm{OMC}_\mathrm{L} = \mathrm{CELF}(r_\mathrm{n}) \cdot \sum_j \mathrm{OMC}_{0,j}

The first-year operating and maintenance cost of a component is a share of its purchase equipment
cost or of its total capital investment, whichever :code:`omc_basis` names. The two differ by the
installation factor, so a share meant for one basis is badly wrong on the other:

.. math::

    \mathrm{OMC}_{0,j} = \mathrm{omc}_j \cdot \mathrm{PEC}_{\mathrm{ref},j}
    \qquad \text{or} \qquad
    \mathrm{OMC}_{0,j} = \mathrm{omc}_j \cdot \mathrm{TCI}_j

*****************************
The cost rate of a component
*****************************

Each component carries its own investment and its own operating cost, spread over the operating hours
of the year:

.. math::

    \dot{Z}^\mathrm{CC}_j = \frac{f_{\mathrm{TCI},j} \cdot \mathrm{PEC}_{\mathrm{ref},j}
    \cdot \mathrm{CRF}}{\tau}
    \qquad
    \dot{Z}^\mathrm{OM}_j = \frac{\mathrm{OMC}_{0,j} \cdot \mathrm{CELF}}{\tau}
    \qquad
    \dot{Z}_j = \dot{Z}^\mathrm{CC}_j + \dot{Z}^\mathrm{OM}_j

Where the factors are given once for the whole plant, this is the same as levelizing the plant and
sharing the result out over the components in proportion to their purchase equipment cost.

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

A cost may be given per unit of exergy or per unit of energy. A price quoted on a heating value, for
example a gas price in currency per MWh, is an energy-based cost and is converted with the ratio of
the energy flow to the exergy flow of that stream.

The levelized total revenue requirement of the plant is the sum of the three:

.. math::

    \mathrm{TRR}_\mathrm{L} = \mathrm{CC}_\mathrm{L} + \mathrm{OMC}_\mathrm{L}
    + \mathrm{FC}_\mathrm{L}

*****************************
Using the class
*****************************

Four inputs have no meaningful default and are required: the purchase equipment costs, the effective
rate of return, the lifetime of the plant and its operating hours. The installation factor and the
maintenance share are required too, since neither can be defaulted without silently changing the
result. Each of them takes one value for the whole plant or one per component.

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
one entry, so its cost, the year it was quoted in and the factors that belong to it cannot drift
apart:

.. code-block:: json

    {
        "i_eff": 0.12,
        "n": 20,
        "tau": 6000,
        "currency": "EUR",
        "r_n": 0.05,

        "reference_year": 2025,
        "cost_index": {"2021": 112.0, "2024": 139.0, "2025": 143.0},

        "f_tci": 4.5,
        "omc_share": 0.015,
        "omc_basis": "PEC",

        "components": {
            "COMP": {"PEC": 300000.0, "cost_year": 2021, "f_tci": 4.2, "omc_share": 0.03},
            "COND": {"PEC": 120000.0, "cost_year": 2024, "f_tci": 6.3},
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
plant-wide maintenance share of 0.015 and :code:`VAL` takes both the plant-wide factor of 4.5 and
that share. A component may be a plain number instead of an object, and so may an entry of
:code:`fuel_costs`; both are then read as the cost with everything else left at its default.

Where every component shares the same assumptions, the file collapses to a list of costs: leave out
:code:`cost_year`, :code:`reference_year` and :code:`cost_index`, and nothing is escalated.

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
    insurance; those enter the year-by-year analysis of the reference and are here absorbed into the
    effective rate of return and the installation factor.
