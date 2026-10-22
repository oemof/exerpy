.. _examples_purchase_costs_label:

*******************************************
Purchased Equipment Costs from Four Sources
*******************************************

.. seealso::

    The methods behind this example: :ref:`Component Sizing <component_sizing_label>`,
    :ref:`purchased equipment costs <purchase_equipment_costs_label>` and :ref:`Economic Analysis
    <economic_analysis_label>`.

An economic analysis starts from the purchased equipment cost :math:`\mathrm{PEC}_j` of every
component :math:`j`. ExerPy ships no cost data, so the costs come from the user, in one of four ways
or a mix of them:

.. list-table::
    :header-rows: 1
    :widths: 22 40 38

    * - Option
      - When to use it
      - What the user provides
    * - 1. Known costs
      - Costs from a source: a manufacturer, the literature, a built plant
      - The cost and its reference year
    * - 2. Scaled from a reference
      - The cost of a reference component of the same type but a different size is known, from the
        literature or a manufacturer
      - The cost, the size and the reference year of the reference component, and which size it refers to
    * - 3. User-defined cost equations
      - A cost function of one or more sizes of a component, from in-house data
      - The equation, in the currency and at the price level of the base year
    * - 4. OpenPyTEA :cite:`Tamarona2026`
      - A first estimate where no data of your own exist
      - The choice of the correlation, where the default for the component class does not fit

This example takes an air source heat pump through each option on its own, from the inputs to the
cost rates :math:`\dot{Z}_j`, and then combines them. All options use the same
economic assumptions, so the cost rates differ only through the purchased equipment costs. How the
analysis turns a purchased equipment cost into a cost rate, step by step, is shown in :ref:`the
previous example <examples_heatpump_exergoeconomic_label>`.

.. warning::

    The known costs, the reference costs, the cost index, the cost equations and the heat transfer
    coefficients of this example are fictitious placeholders, made up for the example. They are not data
    from the literature and give no realistic costs.

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

The example needs TESPy and, for option 4, OpenPyTEA:

.. code-block:: bash

    pip install exerpy[tespy,costs]

Common steps
============

**1. The model and its exergy analysis.** The plant is the TESPy model of the :ref:`air source heat
pump <examples_heatpump_label>`. It delivers 2.1 MW of heat to water heated from 70 °C to 120 °C,
with R245fa as the working fluid.

.. dropdown:: The TESPy model

    .. literalinclude:: /../examples/exergoeconomic_analysis/heatpump/hp_purchase_costs.py
        :language: python
        :start-after: [tespy_model]
        :end-before: [exergy_analysis]

.. literalinclude:: /../examples/exergoeconomic_analysis/heatpump/hp_purchase_costs.py
    :language: python
    :start-after: [exergy_analysis]
    :end-before: [economic]

**2. The economic assumptions.** The effective rate of return :math:`i_\mathrm{eff}`, the lifetime
:math:`n`, the operating hours :math:`\tau`, the installation factor :math:`f_\mathrm{TCI}`, the
maintenance share :math:`\mathrm{omc}`, the escalation rate :math:`r_\mathrm{n}` and the base
year :math:`y_\mathrm{base}` are the same for every option:

.. literalinclude:: /../examples/exergoeconomic_analysis/heatpump/hp_purchase_costs.py
    :language: python
    :start-after: [economic]
    :end-before: [sizes]

**3. The sizes of the components.** Options 2 to 4 need sizes of the components.
:func:`~exerpy.costing.sizes` reads all sizes that the model determines, in SI units; see
:ref:`Component Sizing <component_sizing_label>`. The area of a heat exchanger needs the overall heat
transfer coefficient :math:`U` of each section. ExerPy has no comparable cell for an R245fa condenser
or an air-to-R245fa evaporator, so :math:`U` is given per section by its pair of phases, hot stream first; the
evaporator is sized as an air-cooled exchanger based on its bare-tube area.

.. literalinclude:: /../examples/exergoeconomic_analysis/heatpump/hp_purchase_costs.py
    :language: python
    :start-after: [sizes]
    :end-before: [option1]

.. csv-table:: The sizes the model determines
    :header: "Component", "Sizes"
    :widths: 14 86

    "COMP", "power 894 kW, mass flow 11.06 kg/s, volume flow 3.42 m³/s, pressure ratio 41.8"
    "FAN", "power 705 kW, mass flow 251.8 kg/s, volume flow 202 m³/s, pressure ratio 1.03"
    "PUMP", "power 0.064 kW, mass flow 10 kg/s, volume flow 0.0102 m³/s, pressure ratio 1.01"
    "MOT1, MOT2, MOT3", "power 716 kW, 908 kW and 0.065 kW"
    "COND", "heat 2106 kW, kA 270 kW/K, :math:`\Delta T_\mathrm{lm}` 7.8 K, area 71.7 m²"
    "EVA", "heat 1212 kW, kA 234 kW/K, :math:`\Delta T_\mathrm{lm}` 5.2 K, area 343 m² (bare tube)"
    "VAL", ""

Option 1: known costs
=====================

**What the user provides.** Each cost comes with its reference year :math:`y_{\mathrm{ref},j}`. The analysis carries it
to the base year with a plant cost index :math:`I`, which the user supplies as
``{year: index}``; only the ratio of two entries is used. The index here is a made-up series.

.. literalinclude:: /../examples/exergoeconomic_analysis/heatpump/hp_purchase_costs.py
    :language: python
    :start-after: [option1]
    :end-before: [option1_z]

**From the purchased equipment costs to the cost rates.**

.. literalinclude:: /../examples/exergoeconomic_analysis/heatpump/hp_purchase_costs.py
    :language: python
    :start-after: [option1_z]
    :end-before: [option2]

.. csv-table:: Option 1: purchased equipment costs and cost rates
    :header: "Component", ":math:`\mathrm{PEC}_j` [EUR]", ":math:`y_{\mathrm{ref},j}`", ":math:`\mathrm{PEC}_j` at 2025 [EUR]", ":math:`\dot{Z}_j` [EUR/h]"
    :widths: 16 20 12 26 18

    "COMP", "300 000", "2021", "383 036", "39.85"
    "COND", "120 000", "2021", "153 214", "15.94"
    "EVA", "150 000", "2021", "191 518", "19.93"
    "FAN", "40 000", "2024", "41 151", "4.28"
    "MOT1", "25 000", "2024", "25 719", "2.68"
    "MOT2", "60 000", "2023", "64 511", "6.71"
    "MOT3", "8 000", "2023", "8 602", "0.89"
    "PUMP", "15 000", "2023", "16 128", "1.68"
    "VAL", "5 000", "2023", "5 376", "0.56"
    "Sum", "", "", "", "92.53"

Option 2: scaling the cost of a reference component
===================================================

**What the user provides.** The cost :math:`\mathrm{PEC}_\mathrm{ref}`, the size
:math:`X_\mathrm{ref}` and the reference year of a reference component of the same type, and, with
``size_by``, the size the reference refers to. The analysis reads that size :math:`X` from the model,
scales the cost with the exponent :math:`\alpha`, 0.6 by default, and escalates it from the year
of the reference (see :ref:`Scaling the cost of a reference component <scaled_cost_label>`):

.. math::

    \mathrm{PEC}_j = \mathrm{PEC}_\mathrm{ref} \left(\frac{X_j}{X_\mathrm{ref}}\right)^{\alpha}
    \cdot \frac{I_{y_\mathrm{base}}}{I_{y_{\mathrm{ref},j}}}

The references here refer to different sizes: the power of the compressor, the volume flow of the
fan and the areas of the two heat exchangers, each with the exchanger type and the coefficients of
step 3. ``size_ref`` is in the SI unit of the size.

.. literalinclude:: /../examples/exergoeconomic_analysis/heatpump/hp_purchase_costs.py
    :language: python
    :start-after: [option2]
    :end-before: [option2_z]

**From the purchased equipment costs to the cost rates.** The components without a reference keep
their known costs from option 1. The analysis is given the exergy analysis to read the sizes from.

.. literalinclude:: /../examples/exergoeconomic_analysis/heatpump/hp_purchase_costs.py
    :language: python
    :start-after: [option2_z]
    :end-before: [option3]

.. csv-table:: Option 2: the scaled components, as ``economic_results`` lists them, and their cost rates
    :header: "Component", ":math:`\mathrm{PEC}_\mathrm{ref}` [EUR]", ":math:`X_\mathrm{ref}`", ":math:`X`", ":math:`\alpha`", ":math:`\mathrm{PEC}_j` [EUR]", ":math:`y_{\mathrm{ref},j}`", ":math:`\dot{Z}_j` [EUR/h]"
    :widths: 12 14 14 14 8 14 9 15

    "COMP", "250 000", "600 kW", "894 kW", "0.80", "343 967", "2021", "45.70"
    "FAN", "30 000", "150 m³/s", "202 m³/s", "0.60", "35 862", "2024", "3.84"
    "COND", "90 000", "50 m²", "71.7 m²", "0.60", "111 711", "2023", "12.50"
    "EVA", "120 000", "250 m²", "343 m²", "0.60", "145 194", "2021", "19.29"

With the other components as in option 1, the cost rates sum to 93.84 EUR/h.

Option 3: user-defined cost equations
=====================================

**What the user provides.** A cost equation is an ordinary Python function of the sizes it needs,
here one or two of the sizes of step 3, converted into the units the equation is written in. The
compressor equation takes the power and the pressure ratio, the fan equation the volume flow.
Since the equations are written in the currency and at the price level of the base year, the
costs need no escalation and no cost index. A component the model gives no size for, here the valve, takes a plain value.

.. warning::

    These equations are fictitious placeholders made up for this example. They are not cost correlations
    from the literature; replace them with your own.

.. literalinclude:: /../examples/exergoeconomic_analysis/heatpump/hp_purchase_costs.py
    :language: python
    :start-after: [option3]
    :end-before: [option3_z]

**From the purchased equipment costs to the cost rates.**

.. literalinclude:: /../examples/exergoeconomic_analysis/heatpump/hp_purchase_costs.py
    :language: python
    :start-after: [option3_z]
    :end-before: [option4]

.. csv-table:: Option 3: purchased equipment costs at 2025 and cost rates
    :header: "Component", "Sizes the equation takes", ":math:`\mathrm{PEC}_j` [EUR]", ":math:`\dot{Z}_j` [EUR/h]"
    :widths: 14 40 22 20

    "COMP", "894 kW, pressure ratio 41.8", "400 328", "41.65"
    "COND", "71.7 m²", "29 561", "3.08"
    "EVA", "343 m²", "32 050", "3.33"
    "FAN", "202 m³/s", "62 873", "6.54"
    "MOT1", "716 kW", "32 558", "3.39"
    "MOT2", "908 kW", "39 713", "4.13"
    "MOT3", "0.065 kW", "512", "0.05"
    "PUMP", "0.064 kW", "2 010", "0.21"
    "VAL", "", "5 000", "0.52"
    "Sum", "", "", "62.91"

Option 4: the correlations of OpenPyTEA
=======================================

**What the user provides.** `OpenPyTEA <https://github.com/pbtamarona/OpenPyTEA>`__
:cite:`Tamarona2026` collects published cost correlations for process equipment. ExerPy contains
none of them; they are read from OpenPyTEA at runtime and are subject to its licence. The user
chooses a correlation per component or takes the default for its class:

- **The default correlation or another one.** :func:`~exerpy.costing.default_correlation` suggests one correlation per
  component class, and :func:`~exerpy.costing.correlations` lists the alternatives, e.g.
  ``costing.correlations("Compressor")``. Here the compressor is a screw compressor, whose
  correlation includes its electric motor, so the motor :code:`MOT2` costs nothing on its own.
- **The size of the correlation.** :func:`~exerpy.costing.estimate` takes the size whose dimension
  matches the units of the correlation and converts it into those units: the power of the
  compressor into horsepower, the volume flow at the fan inlet into ACFM (actual cubic feet per
  minute), the areas of the exchangers into m² or ft². For a correlation based on a size that the
  model does not provide, the size is given by hand as ``value``.
- **Outside the range.** A size below or above the range of a correlation is extrapolated from the
  nearest bound with a scaling exponent (``outside="scale"``, the default) or, above the range,
  split into identical units in parallel (``outside="parallel"``), as for the fan.
- **The heat exchangers** take a plate correlation and the air-cooled fin-fan correlation, which is
  based on the bare-tube area, each with the coefficients of step 3.

.. literalinclude:: /../examples/exergoeconomic_analysis/heatpump/hp_purchase_costs.py
    :language: python
    :start-after: [option4]
    :end-before: [option4_z]

.. csv-table:: Option 4: the correlations, the sizes in their units and how the sizes fit their ranges
    :header: "Component", "Correlation", "Size", "Fit", "Method"
    :widths: 10 44 24 10 12

    "COMP", "``screw_compressor_electric_motor_seider_2013``", "1199 hp", "above", "scaled"
    "FAN", "``centrifugal_backward_curved_fan_head_9-15_seider_2013``", "427 942 ACFM", "above", "parallel"
    "COND", "``plate_frame_hx_towler_2010``", "71.7 m²", "in range", "correlation"
    "EVA", "``air_cooled_finfan_seider_2013``", "3697 ft² (bare tube)", "in range", "correlation"
    "MOT1", "``totally_enclosed_motor_ulrich_2003``", "716 kW", "in range", "correlation"
    "MOT3", "``totally_enclosed_motor_ulrich_2003``", "0.065 kW", "below", "scaled"
    "PUMP", "``centrifugal_pump_turton_2001``", "0.064 kW", "below", "scaled"

**From the purchased equipment costs to the cost rates.** The costs are in US dollars of the year of
each correlation. They are converted into euros at the exchange rate of that year
(:func:`~exerpy.costing.per_dollar`), which remains the reference year, and escalated with the cost index of
OpenPyTEA (:func:`~exerpy.costing.cost_index`). That index ends in 2024; the analysis bridges the last
year with the escalation rate :math:`r_\mathrm{n}` and reports this.

.. literalinclude:: /../examples/exergoeconomic_analysis/heatpump/hp_purchase_costs.py
    :language: python
    :start-after: [option4_z]
    :end-before: [combined]

.. csv-table:: Option 4: purchased equipment costs and cost rates
    :header: "Component", ":math:`\mathrm{PEC}_j` [EUR]", ":math:`y_{\mathrm{ref},j}`", ":math:`\mathrm{PEC}_j` at 2025 [EUR]", ":math:`\dot{Z}_j` [EUR/h]"
    :widths: 16 20 12 26 18

    "COMP", "461 509", "2013", "683 355", "71.10"
    "COND", "10 377", "2010", "15 826", "1.65"
    "EVA", "57 078", "2013", "84 515", "8.79"
    "FAN", "165 425", "2013", "244 944", "25.49"
    "MOT1", "43 703", "2003", "91 320", "9.50"
    "MOT2", "0", "", "0", "0.00"
    "MOT3", "15", "2003", "31", "0.00"
    "PUMP", "525", "2001", "1 119", "0.12"
    "VAL", "5 000", "2025", "5 000", "0.52"
    "Sum", "", "", "", "117.17"

Mixing the sources
==================

The options combine freely, component by component: here the known costs for the compressor and its
motor, and OpenPyTEA for the rest. Each cost keeps its own reference year.

.. literalinclude:: /../examples/exergoeconomic_analysis/heatpump/hp_purchase_costs.py
    :language: python
    :start-after: [combined]
    :end-before: [exergoeconomic_run]

The combined costs give :math:`\sum \dot{Z}_j = 89.63` EUR/h. One plant cost index carries all of
them to the base year, here the index of OpenPyTEA. The known cost of the compressor therefore gives
:math:`\dot{Z} = 36.99` EUR/h here, against 39.85 EUR/h in option 1, where the index of option 1
escalated it.

The exergoeconomic analysis
===========================

Any of the sets can provide the cost rates for an exergoeconomic analysis; the combined one is used here.

.. literalinclude:: /../examples/exergoeconomic_analysis/heatpump/hp_purchase_costs.py
    :language: python
    :start-after: [exergoeconomic_run]
    :end-before: [end]

With the combined costs the product of the plant, the heat taken up by the water, costs 186.86
EUR/GJ, compared with 40.35 EUR/GJ for the levelized electricity, and the evaporator has the largest
cost rate of exergy destruction, 75.84 EUR/h at an exergoeconomic factor of 10.4 %. The results are
read as in :ref:`the previous example <examples_heatpump_exergoeconomic_label>`; since they rest on
placeholder costs, they illustrate the procedure only.

Full code
=========

.. dropdown:: Full code of this example

    .. literalinclude:: /../examples/exergoeconomic_analysis/heatpump/hp_purchase_costs.py
        :language: python
