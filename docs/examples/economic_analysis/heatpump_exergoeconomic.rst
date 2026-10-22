.. _examples_heatpump_exergoeconomic_label:

***********************************************
From Equipment Costs to the Cost of the Product
***********************************************

.. seealso::

    The methods behind this example: :ref:`Economic Analysis <economic_analysis_label>` and :ref:`Exergoeconomic Analysis <exergoeconomic_analysis_label>`.

An exergoeconomic analysis needs the cost rate :math:`\dot{Z}` of every component, in currency per
hour. That rate is rarely what an engineer has at hand: what is known is the purchased equipment cost
(PEC) of a component and the year it refers to, its reference year. This example shows, step by step, how
:class:`~exerpy.analyses.EconomicAnalysis` turns the purchased equipment costs into the cost rates
using the total revenue requirement method of Bejan et al. :cite:`Bejan1996`, and runs the whole way
from the equipment costs of an air source heat pump to the specific cost of the heat it delivers.

.. warning::

    Every cost figure in this example is a placeholder chosen to show the workflow, the cost index
    included. The results illustrate how the analysis works and how to read its output; they say
    nothing about the costs of a real heat pump.

Where the purchased equipment costs come from (known costs, scaled costs of reference components,
user-defined cost equations or the correlations of OpenPyTEA :cite:`Tamarona2026`) is the subject of
:ref:`the next example
<examples_purchase_costs_label>`.

The flowsheet below names the components and the streams used throughout this example.

.. figure:: /_static/images/flowsheets/heatpump.svg
    :align: center
    :alt: Heat pump flowsheet
    :figclass: only-light

    Figure: Flowsheet of the air source heat pump

.. figure:: /_static/images/flowsheets/heatpump_darkmode.svg
    :align: center
    :alt: Heat pump flowsheet
    :figclass: only-dark

    Figure: Flowsheet of the air source heat pump

1. **The exergy analysis**

The plant is the :ref:`air source heat pump <examples_heatpump_label>`; the analysis reads its
exported model:

.. literalinclude:: /../examples/exergoeconomic_analysis/heatpump/hp_exergoeconomic.py
    :language: python
    :start-after: [exergy_analysis]
    :end-before: [economic_setup]

2. **The cost assumptions**

The assumptions live in a JSON file, so everything about one component stays in one place. Six
inputs have no meaningful default and are required: the purchased equipment costs
:math:`\mathrm{PEC}_j`, the effective rate of return :math:`i_\mathrm{eff}`, the lifetime of the plant
:math:`n`, its operating hours :math:`\tau`, the installation factor :math:`f_\mathrm{TCI}` and the
maintenance share :math:`\mathrm{omc}`. The operating hours are among them because they scale every
cost rate: a plant running 2000 h/a and one running 8000 h/a differ by a factor of four.

Where every component shares the same assumptions, the file is short. A value given at the top level
applies to the whole plant, and a component is then just its cost:

.. literalinclude:: /../examples/exergoeconomic_analysis/heatpump/hp_costs_simple.json
    :language: json

Where they do not, each component names only what differs from the plant-wide value. Here the costs
come from three different years, the installation effort of a heat exchanger is not that of a motor,
and the rotating machines need more maintenance than the heat exchangers:

.. literalinclude:: /../examples/exergoeconomic_analysis/heatpump/hp_costs_detailed.json
    :language: json

:code:`PUMP` names no :code:`f_tci` and the motors name no :code:`omc_share`, so those fall back to
the value given for the whole plant. A component entry may be a plain number instead of an object,
and so may an entry of :code:`fuel_costs`.

.. literalinclude:: /../examples/exergoeconomic_analysis/heatpump/hp_exergoeconomic.py
    :language: python
    :start-after: [economic_setup]
    :end-before: [economic_results]

3. **From the equipment cost to the cost rate, step by step**

Every component goes through the same five steps. They are shown here for the compressor
:code:`COMP` of the detailed file, 300 000 EUR in 2021:

1. **Escalate to the base year.** A cost from another year is carried to the base
   year with the ratio of the plant cost index of the two years,
   :math:`\mathrm{PEC}_\mathrm{base} = \mathrm{PEC} \cdot I_{2025} / I_{2021}`.
2. **Scale it up to the total capital investment.** The installation factor :math:`f_\mathrm{TCI}`
   adds installation, piping, instrumentation, engineering, contingency, start-up and working capital,
   :math:`\mathrm{TCI} = f_\mathrm{TCI} \cdot \mathrm{PEC}_\mathrm{base}`.
3. **Spread the investment over the lifetime.** The capital recovery factor turns the investment
   into equal annual carrying charges,
   :math:`\mathrm{CRF} = i_\mathrm{eff} (1 + i_\mathrm{eff})^n / ((1 + i_\mathrm{eff})^n - 1)`.
4. **Levelize the operating and maintenance cost.** Its first-year value is a share of the
   equipment cost and escalates at :math:`r_\mathrm{n}` per year; the constant-escalation
   levelization factor turns it into an equal annual amount,
   :math:`\mathrm{CELF} = k (1 - k^n) / (1 - k) \cdot \mathrm{CRF}` with
   :math:`k = (1 + r_\mathrm{n}) / (1 + i_\mathrm{eff})`.
5. **Divide by the operating hours.** Dividing both annual amounts by :math:`\tau` gives the cost rates
   :math:`\dot{Z}^\mathrm{CC}` and :math:`\dot{Z}^\mathrm{OM}`, and their sum is :math:`\dot{Z}`.

.. csv-table:: The compressor from its purchased equipment cost to its cost rate
    :header: "Step", "Operation", "Result", "Unit"
    :widths: 30 34 18 12

    "Purchased equipment cost, 2021", "", "300 000", "EUR"
    "1. at the base year 2025", ":math:`\times\, I_{2025}/I_{2021} = 143/112`", "383 036", "EUR"
    "2. total capital investment", ":math:`\times\, f_\mathrm{TCI} = 4.2`", "1 608 750", "EUR"
    "3. carrying charges", ":math:`\times\, \mathrm{CRF} = 0.1339`", "215 377", "EUR/a"
    "4. O&M cost, first year", ":math:`0.03 \times 383\,036`", "11 491", "EUR/a"
    "4. O&M cost, levelized", ":math:`\times\, \mathrm{CELF} = 1.4558`", "16 729", "EUR/a"
    "5. :math:`\dot{Z}^\mathrm{CC}`", ":math:`215\,377 \,/\, 6000`", "35.90", "EUR/h"
    "5. :math:`\dot{Z}^\mathrm{OM}`", ":math:`16\,729 \,/\, 6000`", "2.79", "EUR/h"
    ":math:`\dot{Z}`", ":math:`\dot{Z}^\mathrm{CC} + \dot{Z}^\mathrm{OM}`", "38.68", "EUR/h"

The lifetime :math:`n = 20` years, the effective rate of return :math:`i_\mathrm{eff} = 0.12`, the
escalation rate :math:`r_\mathrm{n} = 0.05` and the operating hours :math:`\tau = 6000` h/a are the
values of the detailed file. :meth:`~exerpy.analyses.EconomicAnalysis.economic_results` prints the
same steps for every component and for the plant:

.. literalinclude:: /../examples/exergoeconomic_analysis/heatpump/hp_exergoeconomic.py
    :language: python
    :start-after: [economic_results]
    :end-before: [exergoeconomic_run]

.. csv-table:: Cost rates of the components, from the detailed file
    :header: "Component", "reference year", ":math:`\mathrm{PEC}` [EUR]", ":math:`\mathrm{PEC}` at 2025 [EUR]", ":math:`f_\mathrm{TCI}`", ":math:`\mathrm{omc}`", ":math:`\dot{Z}^\mathrm{CC}` [EUR/h]", ":math:`\dot{Z}^\mathrm{OM}` [EUR/h]", ":math:`\dot{Z}` [EUR/h]"
    :widths: 12 10 14 16 10 10 16 16 12

    "COMP", "2021", "300 000", "383 036", "4.2", "0.03", "35.90", "2.79", "38.68"
    "COND", "2021", "120 000", "153 214", "6.3", "0.01", "21.54", "0.37", "21.91"
    "EVA", "2021", "150 000", "191 518", "6.3", "0.01", "26.92", "0.46", "27.39"
    "FAN", "2024", "40 000", "41 151", "3.8", "0.025", "3.49", "0.25", "3.74"
    "MOT1", "2024", "25 000", "25 719", "2.2", "0.015", "1.26", "0.09", "1.36"
    "PUMP", "2023", "15 000", "16 128", "4.5", "0.025", "1.62", "0.10", "1.72"
    "VAL", "2023", "5 000", "5 376", "3.5", "0.005", "0.42", "0.01", "0.43"
    "MOT2", "2023", "60 000", "64 511", "2.2", "0.015", "3.17", "0.23", "3.40"
    "MOT3", "2023", "8 000", "8 602", "2.2", "0.015", "0.42", "0.03", "0.45"
    "TOT", "", "723 000", "889 255", "", "", "94.74", "4.34", "99.07"

.. csv-table:: Levelized costs of the plant, from the detailed file
    :header: "", "value", "unit"
    :widths: 26 18 12

    ":math:`\mathrm{PEC}` at its reference year", "723 000", "EUR"
    ":math:`\mathrm{PEC}` at the base year", "889 255", "EUR"
    ":math:`\mathrm{TCI}`", "4 245 758", "EUR"
    ":math:`\mathrm{CRF}`", "0.1339", ""
    ":math:`\mathrm{CELF}`", "1.4558", ""
    "carrying charges, levelized", "568 417", "EUR/a"
    "O&M cost, levelized", "26 030", "EUR/a"
    "fuel cost, levelized", "1 415 429", "EUR/a"
    ":math:`\mathrm{TRR}`, levelized", "2 009 876", "EUR/a"
    ":math:`\sum \dot{Z}`", "99.07", "EUR/h"

**How to read the tables.** Each row of the first table is one component: its reference year
:math:`y_{\mathrm{ref},j}`, its purchased equipment cost :math:`\mathrm{PEC}_j` at that year and at the base
year, the factors :math:`f_\mathrm{TCI}` and :math:`\mathrm{omc}` it was given, and the two parts of
its cost rate. The second table shows the levelized costs of the whole plant. The two tables are
consistent: the sum of the cost rates equals the levelized carrying charges plus the operating and
maintenance costs, divided by the operating hours,
:math:`\sum \dot{Z} = (\mathrm{CC}_\mathrm{L} + \mathrm{OMC}_\mathrm{L}) / \tau
= (568\,417 + 26\,030) / 6000 = 99.07` EUR/h.

The simple file describes the same plant with other placeholder inputs, one reference year and one
:math:`f_\mathrm{TCI}` for all components, and gives :math:`\sum \dot{Z} = 104.59` EUR/h. The
difference comes only from the different inputs of the two files.

4. **The cost of the fuel is levelized too**

The electricity is bought over the whole lifetime of the plant and its price escalates at its own rate, so the
cost the exergoeconomic analysis works with is the levelized one:

.. math::

    c_\mathrm{L} = c_0 \cdot \mathrm{CELF}(r_{\mathrm{n},\mathrm{fuel}})

With :math:`c_0 = 30` EUR/GJ and :math:`r_\mathrm{n} = 0.04` per year, the electricity enters the
analysis at 40.35 EUR/GJ rather than at 30, because its price escalates over the lifetime. Since the
fuel and the investment are levelized over the same lifetime, the resulting cost of the product is a
levelized cost as well.

5. **The exergoeconomic analysis**

:meth:`~exerpy.analyses.EconomicAnalysis.compute_costs` returns the cost rates of the components and
the costs of the entering streams in one dictionary, keyed the way
:meth:`~exerpy.analyses.ExergoeconomicAnalysis.run` expects them. It checks both against the plant: a
component without an equipment cost, a cost for something that is not in the plant, a cost for a
component that carries no cost balance and a stream entering the plant without a cost are all
reported instead of silently changing the result.

.. literalinclude:: /../examples/exergoeconomic_analysis/heatpump/hp_exergoeconomic.py
    :language: python
    :start-after: [exergoeconomic_run]
    :end-before: [display_results]

.. csv-table:: The five components with the highest cost rate
    :header: "Component", ":math:`\dot{C}_\mathrm{D}` [EUR/h]", ":math:`\dot{Z}` [EUR/h]", ":math:`\dot{C}_\mathrm{D}+\dot{Z}` [EUR/h]", ":math:`f` [%]", ":math:`c_\mathrm{F}` [EUR/GJ]", ":math:`c_\mathrm{P}` [EUR/GJ]"
    :widths: 14 16 14 20 10 14 14

    "EVA", "233.67", "27.39", "261.06", "10.5", "100.31", "n/a"
    "COMP", "20.79", "38.68", "59.48", "65.0", "45.91", "109.21"
    "COND", "35.97", "21.91", "57.88", "37.9", "109.21", "190.68"
    "VAL", "56.85", "0.43", "57.28", "0.7", "109.21", "n/a"
    "FAN", "17.13", "3.74", "20.87", "17.9", "45.39", "99.59"

**How to read the table.** The components are ranked by :math:`\dot{C}_\mathrm{D} + \dot{Z}`, the
cost rate of their exergy destruction and of their equipment together. The exergoeconomic factor :math:`f = \dot{Z} / (\dot{Z} + \dot{C}_\mathrm{D})` tells which part
dominates the total cost rate of a component. Following Bejan et al. :cite:`Bejan1996`, a low
:math:`f` points to improving the efficiency of the component, even at a higher investment, and a
high :math:`f` to reducing its investment, even at some loss of efficiency. With the placeholder costs of this example, the evaporator has
:math:`f = 10.5` %, so its total cost rate is mostly the cost of its exergy destruction, and the
compressor has :math:`f = 65.0` %, so its total cost rate is mostly investment. The evaporator and
the valve are dissipative components: the evaporator passes heat from air at the ambient temperature
to the working fluid below it. Neither has a product or a :math:`c_\mathrm{P}`, and their cost is
passed on to the components they serve.

The product of the plant, the heat taken up by the water from stream 21 to stream 23, costs
192.28 EUR/GJ. With other cost inputs, every number in this section
changes, the ranking included; the example shows the procedure, not a result for real heat pumps.

Full code
=========

.. dropdown:: Full code of this example

    .. literalinclude:: /../examples/exergoeconomic_analysis/heatpump/hp_exergoeconomic.py
        :language: python
