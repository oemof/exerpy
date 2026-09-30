.. _examples_heatpump_exergoeconomic_label:

***********************************************
From Equipment Costs to the Cost of the Product
***********************************************

The other exergoeconomic examples take the cost rate :math:`\dot{Z}` of every component as an input.
That rate is rarely what an engineer has at hand: what is known is what the equipment costs, and in
which year it was quoted. :class:`~exerpy.analyses.EconomicAnalysis` closes that gap with the total
revenue requirement method of Bejan et al. :cite:`Bejan1996`, and this example runs the whole way
from the equipment costs of an air source heat pump to the specific cost of the heat it delivers.

Every cost figure in this example is a placeholder, the cost index included.

1. **The exergy analysis**

The plant is the :ref:`air source heat pump <examples_heatpump_label>`, costed from its exported
model:

.. literalinclude:: /../examples/exergoeconomic_analysis/heatpump/hp_exergoeconomic.py
    :language: python
    :start-after: [exergy_analysis]
    :end-before: [economic_setup]

2. **The cost assumptions**

The assumptions live in a JSON file, so everything about one component stays in one place. Four
inputs have no meaningful default and are required: the purchase equipment costs, the effective rate
of return, the lifetime of the plant and its operating hours. The operating hours are among them
because they scale every cost rate: a plant running 2000 h/a and one running 8000 h/a differ by a
factor of four.

Where every component shares the same assumptions, the file is short. A value given at the top level
applies to the whole plant and a component is then just its cost:

.. literalinclude:: /../examples/exergoeconomic_analysis/heatpump/hp_costs_simple.json
    :language: json

Where they do not, each component names only what differs from the plant-wide value. Here the quotes
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

3. **From the equipment cost to the cost rate**

Every component is carried to the reference year with the plant cost index, grown into its share of
the total capital investment and levelized over the lifetime of the plant:

.. math::

    \mathrm{PEC}_{\mathrm{ref},j} = \mathrm{PEC}_j \cdot \frac{I_\mathrm{ref}}{I_{y(j)}}
    \qquad
    \dot{Z}^\mathrm{CC}_j = \frac{f_{\mathrm{TCI},j} \cdot \mathrm{PEC}_{\mathrm{ref},j}
    \cdot \mathrm{CRF}}{\tau}
    \qquad
    \dot{Z}^\mathrm{OM}_j = \frac{\mathrm{omc}_j \cdot \mathrm{PEC}_{\mathrm{ref},j}
    \cdot \mathrm{CELF}}{\tau}

.. literalinclude:: /../examples/exergoeconomic_analysis/heatpump/hp_exergoeconomic.py
    :language: python
    :start-after: [economic_results]
    :end-before: [exergoeconomic_run]

.. csv-table:: Cost rates of the components, from the detailed file
    :header: "Component", "cost year", ":math:`\mathrm{PEC}` [EUR]", ":math:`\mathrm{PEC}` at 2025 [EUR]", ":math:`f_\mathrm{TCI}`", ":math:`\mathrm{omc}`", ":math:`\dot{Z}^\mathrm{CC}` [EUR/h]", ":math:`\dot{Z}^\mathrm{OM}` [EUR/h]", ":math:`\dot{Z}` [EUR/h]"
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

    ":math:`\mathrm{PEC}` as quoted", "723 000", "EUR"
    ":math:`\mathrm{PEC}` at the reference year", "889 255", "EUR"
    ":math:`\mathrm{TCI}`", "4 245 758", "EUR"
    ":math:`\mathrm{CRF}`", "0.1339", "-"
    ":math:`\mathrm{CELF}`", "1.4558", "-"
    "carrying charges, levelized", "568 417", "EUR/a"
    "O&M cost, levelized", "26 030", "EUR/a"
    "fuel cost, levelized", "1 415 429", "EUR/a"
    ":math:`\mathrm{TRR}`, levelized", "2 009 876", "EUR/a"
    ":math:`\sum \dot{Z}`", "99.07", "EUR/h"

The two files describe the same plant and do not give the same answer. The detailed one escalates the
equipment cost by 23 %, from 723 000 to 889 255 EUR, and still ends at a *lower* investment, 4.25
against 4.57 million EUR, and a lower :math:`\sum \dot{Z}`, 99.07 against 104.59 EUR/h. The reason is
the installation factor: the motors and the valve carry 2.2 to 3.5 rather than a blanket 6.32, and
that outweighs the escalation. A single factor for a plant with a lot of small electrical equipment
overstates the investment.

4. **The cost of the fuel is levelized too**

The electricity is bought over the whole lifetime of the plant and escalates at its own rate, so the
cost the exergoeconomic analysis works with is the levelized one:

.. math::

    c_\mathrm{L} = c_0 \cdot \mathrm{CELF}(r_{\mathrm{n},\mathrm{fuel}})

With :math:`c_0 = 30` EUR/GJ and :math:`r_\mathrm{n} = 0.04` per year, the electricity enters the
analysis at 40.35 EUR/GJ rather than at 30. Levelizing the fuel and the investment over the same
lifetime is what makes the resulting cost of the product a levelized cost as well; leaving the fuel
at its first-year price would understate it.

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

The evaporator leads by a wide margin, and its exergoeconomic factor of 10.5 % says that nearly all
of that cost is exergy destruction rather than investment: it is the component to improve
thermodynamically. The compressor is the opposite case at 65.0 %, where a cheaper machine would help
more than a more efficient one. The valve is a dissipative component, so it has no product and no
:math:`c_\mathrm{P}`; its 57.28 EUR/h is charged on to the components it serves.

The heat leaves the plant at 129.00 EUR/GJ, against 235.90 EUR/h of electricity bought and 99.07
EUR/h of investment and maintenance.

.. note::

    A cost rate follows the purchase equipment cost of its component, so a component with a large
    :math:`\dot{Z}` has it because its equipment is expensive and its installation factor is high.
    Where a component is installed with an effort quite unlike the rest of the plant, it is worth
    giving it its own :code:`f_tci` rather than letting it take the plant-wide one.
