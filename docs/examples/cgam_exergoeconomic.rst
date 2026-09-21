.. _examples_cgam_exergoeconomic_label:

**************************************
CGAM Process (Exergoeconomic Analysis)
**************************************

This tutorial demonstrates how to perform an exergoeconomic analysis using ExerPy with
manually defined component and stream costs. 

.. note::

    This tutorial builds upon the :ref:`CGAM Process exergy analysis example <examples_cgam_label>` and uses 
    data imported from a previously saved JSON file. Make sure you understand how to set up exergy analysis 
    from JSON data before proceeding.


1. **Exergy Analysis (Prerequisite)**

Perform the exergy analysis. Note that the JSON example file already contains pre-computed
thermal and mechanical exergy values, so :code:`split_physical_exergy` defaults to :code:`True`.
The analysis runs without the split as well; see
:ref:`Split Physical Exergy in Exergoeconomics <examples_split_physical_exergy_label>` for what the
two settings change:

.. literalinclude:: /../examples/exergoeconomic_analysis/cgam/cgam_exergoeconomic.py
    :language: python
    :start-after: [exergy_analysis_section]
    :end-before: [exergoeconomic_setup]

2. **Define Costs and Run the Exergoeconomic Analysis**

Create the :class:`~exerpy.analyses.ExergoeconomicAnalysis` instance and define all required costs
directly in a dictionary:

.. literalinclude:: /../examples/exergoeconomic_analysis/cgam/cgam_exergoeconomic.py
    :language: python
    :start-after: [exergoeconomic_setup]
    :end-before: [display_results]

The cost dictionary requires two types of entries:

- **Component investment costs** (:code:`<name>_Z`): the cost rate in currency/h for each component.
  These represent the annualized capital investment plus operating and maintenance costs.
- **Input stream costs** (:code:`<name>_c`): the specific cost in currency/GJ for each stream
  entering the system boundary. Ambient air is typically assigned a cost of 0.0.

.. _cgam_cost_basis:

**The cost basis**

The numbers above are the cost model of the CGAM problem itself :cite:`Valero1994`. The purchase
equipment costs follow Table 1 of the paper with the constants of its Table 2, evaluated at the
operating point of this model, and are annualized with

.. math::

    \dot{Z}_i = Z_i \, \frac{\mathrm{CRF} \cdot \varphi}{N}
    \qquad
    \mathrm{CRF} = 0.182, \quad \varphi = 1.06, \quad N = 8000\,\mathrm{h/yr}

The fuel is natural gas at 0.004 USD/MJ on a lower heating value basis. ExerPy prices a boundary
stream per unit of *exergy*, so with :math:`\mathrm{LHV} = 50000` kJ/kg and
:math:`e_\mathrm{f} = 51850` kJ/kg the same cost rate corresponds to 3.8635 USD/GJ of exergy.
The paper gives no cost equation for the generator and no cost for the feedwater, so both are zero
here.

The paper reports a single purchase cost for the heat recovery steam generator, while the model has
an evaporator and an economizer as separate components. The 724,508 USD of the HRSG are therefore
split over the two: each section keeps its own :math:`C_{51}(\dot{Q}/\Delta T_\mathrm{LM})^{0.8}`
term, the steam flow term :math:`C_{52}\dot{m}_\mathrm{st}` goes to the evaporator, and the gas
side term :math:`C_{53}\dot{m}_\mathrm{g}^{1.2}` is shared equally. This split is a convention of
this example, not of the paper.

.. note::

    Table 2 of the paper lists :math:`U = 18` kW/(m²K) for the air preheater, which gives a heat
    transfer area of 7.7 m² and a purchase cost of 13,000 USD. Reading it as 18 W/(m²K) gives
    7745 m² and 828,260 USD, which is the 0.8277 × 10\ :sup:`6` USD of Table 6 of the paper. The
    value used here is therefore :math:`U = 0.018` kW/(m²K).

**Checked against the paper**

Evaluated at the optimal design of the paper (its Tables 3 to 5), the cost model above reproduces
the purchase costs the paper reports in its Table 6:

.. csv-table:: Purchase equipment cost at the optimal design of the paper
    :header: "Component", "this cost model [USD]", "Table 6 [USD]", "deviation [%]"
    :widths: 24 20 20 16

    "Air compressor", "1,348,648", "1,348,000", "0.05"
    "Combustion chamber", "146,905", "146,900", "0.00"
    "Gas turbine", "1,928,300", "1,927,000", "0.07"
    "Air preheater", "828,260", "827,700", "0.07"
    "Heat recovery steam generator", "1,198,817", "1,202,000", "-0.26"
    "Investment cost rate [USD/s]", "0.036514", "0.036520", "-0.02"

The model analysed here is the base case of the CGAM problem
(:math:`P_2/P_1 = 10`, :math:`\eta_\mathrm{AC} = \eta_\mathrm{GT} = 0.86`,
:math:`T_3 = 850` K, :math:`T_4 = 1520` K), not the optimal design, so its cost rates are the
slightly higher ones that the optimization of the paper sets out to reduce:

.. csv-table:: Cost rate of the plant in USD/s
    :header: "", "base case (this example)", "optimal design (Table 6)"
    :widths: 30 24 24

    "Fuel cost rate", "0.328863", "0.325489"
    "Investment cost rate", "0.037129", "0.036520"
    "Total cost rate", "0.365991", "0.362009"

3. **Display and Evaluate Results**

.. literalinclude:: /../examples/exergoeconomic_analysis/cgam/cgam_exergoeconomic.py
    :language: python
    :start-after: [display_results]
    :end-before: [end]

The :code:`evaluate_results()` method ranks components by their total cost rate
(:math:`\dot{C}_D + \dot{Z}`) to identify the most promising targets for optimization.
You can sort by different criteria using the :code:`sort_by` parameter:

.. code-block:: python

    # Sort by cost of exergy destruction only
    eco.evaluate_results(sort_by="C_D", top_n=3)

    # Sort by exergoeconomic factor
    eco.evaluate_results(sort_by="f", top_n=3)


.. seealso::

    The same model is costed with and without split physical exergy in
    :ref:`Split Physical Exergy in Exergoeconomics <examples_split_physical_exergy_label>`.
