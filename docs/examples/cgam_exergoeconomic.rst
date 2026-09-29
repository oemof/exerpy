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

The CGAM problem :cite:`Valero1994` defines the plant, its operating point and the correlations for
the purchase equipment costs of its components. The cost rates used here are the ones Kelly
:cite:`Kelly2008` obtained by evaluating that cost model for this base case, so that the results of
this example can be compared with the ones published there. Both works turn a purchase equipment
cost into a cost rate the same way,

.. math::

    \dot{Z}_i = \mathrm{PEC}_i \, \frac{\mathrm{CRF} \cdot \varphi}{N}

where :math:`\mathrm{CRF} = 0.182` is the annual capital recovery factor, :math:`\varphi = 1.06`
the maintenance factor, which adds the operation and maintenance expenses as a flat surcharge on
the capital cost, and :math:`N = 8000\,\mathrm{h/yr}` the operating hours per year. Note that the
purchase equipment cost is annualized directly: it is not scaled up to a total capital investment
first, as the levelization of Bejan, Tsatsaronis and Moran :cite:`Bejan1996` does.

.. csv-table:: Investment cost of the components
    :header: "Component", "name", ":math:`\dot{Z}` [USD/h]", ":math:`\mathrm{PEC}` implied [USD]"
    :widths: 26 12 20 22

    "Air compressor", "AC", "56.99", "2,363,259"
    "Combustion chamber", "CC", "4.40", "182,459"
    "Gas turbine", "EXP", "48.16", "1,997,097"
    "Air preheater", "APH", "12.26", "508,397"
    "Evaporator", "EV", "11.476", "475,899"
    "Economizer", "PH", "5.454", "226,154"
    "Generator", "GEN", "0.0", "--"

The fuel is natural gas at 0.004 USD/MJ on a lower heating value basis. ExerPy prices a boundary
stream per unit of *exergy*, so with :math:`\mathrm{LHV} = 50000` kJ/kg and
:math:`e_\mathrm{f} = 51850` kJ/kg the same cost rate corresponds to the 3.8635 USD/GJ of the cost
dictionary. The ambient air and the feedwater enter free of charge, and neither work gives a cost
equation for the generator, so its cost rate is zero.

Both references report a single cost rate for the heat recovery steam generator, 16.93 USD/h, while
the model has an evaporator and an economizer as separate components. It is split over the two in
the ratio of the purchase equipment costs of their sections, 67.8 % to 32.2 %, which follows from
the correlation of the paper. This split is a convention of this example.

**What this example computes**

The plant analysed here is the base case of the CGAM problem:
:math:`P_2/P_1 = 10`, :math:`\eta_\mathrm{AC} = \eta_\mathrm{GT} = 0.86`, :math:`T_3 = 850` K and
:math:`T_4 = 1520` K, delivering 30 MW of power and 14 kg/s of saturated steam at 20 bar.


3. **Display and Evaluate Results**

.. literalinclude:: /../examples/exergoeconomic_analysis/cgam/cgam_exergoeconomic.py
    :language: python
    :start-after: [display_results]
    :end-before: [end]

:code:`exergoeconomic_results()` prints the exergy and the cost results of every component and of
the whole plant. The cost part of that table is:

.. csv-table:: Cost rates of the components in USD/h
    :header: "Component", ":math:`\dot{C}_\mathrm{F}`", ":math:`\dot{C}_\mathrm{P}`", ":math:`\dot{C}_\mathrm{D}`", ":math:`\dot{Z}`", ":math:`\dot{C}_\mathrm{D}+\dot{Z}`"
    :widths: 16 16 16 16 16 18

    "AC", "856.59", "919.57", "60.66", "56.99", "117.65"
    "APH", "411.94", "431.50", "63.29", "12.26", "75.55"
    "CC", "1220.96", "1297.55", "367.67", "4.40", "372.07"
    "EV", "371.29", "395.84", "112.38", "11.48", "123.85"
    "EXP", "1666.30", "1723.00", "79.63", "48.16", "127.79"
    "GEN", "866.41", "866.41", "0.00", "0.00", "0.00"
    "PH", "101.65", "n/a", "101.65", "5.45", "107.10"
    "TOT", "1183.91", "1322.65", "548.78", "138.74", "687.52"

.. csv-table:: Specific costs in USD/GJ and exergoeconomic indicators in %
    :header: "Component", ":math:`\dot{E}_\mathrm{D}` [kW]", ":math:`c_\mathrm{F}`", ":math:`c_\mathrm{P}`", ":math:`f`", ":math:`r`"
    :widths: 16 16 16 16 16 16

    "AC", "2100.5", "8.022", "9.269", "48.439", "15.535"
    "APH", "2559.6", "6.868", "8.500", "16.228", "23.762"
    "CC", "25314.3", "4.034", "6.135", "1.183", "52.065"
    "EV", "4586.8", "6.806", "10.405", "9.266", "52.889"
    "EXP", "2994.1", "7.388", "8.022", "37.687", "8.592"
    "GEN", "0.0", "8.022", "8.022", "0.000", "0.000"
    "PH", "1911.4", "14.773", "n/a", "5.092", "n/a"
    "TOT", "39466.7", "3.862", "8.581", "20.180", "122.165"

The plant converts fuel at 3.862 USD/GJ into a product at 8.581 USD/GJ. The combustion chamber
dominates the cost of the exergy destruction with 367.67 USD/h at an exergoeconomic factor of
1.2 %, so its cost is caused almost entirely by irreversibility and not by its investment — the
classic result for the CGAM plant. The compressor and the gas turbine are the opposite case, with
:math:`f` around 38 to 48 %: there the investment carries a large share of the cost, and spending
more on them pays off only if it buys efficiency elsewhere.

**Compared with the literature**

Because the investment costs are the ones of Kelly :cite:`Kelly2008`, the results can be compared
with the ones published there directly. What is compared is then the exergoeconomic method itself
and the underlying thermodynamics, not the cost correlations:

.. csv-table:: Comparison with the conventional exergoeconomic analysis of Kelly (2008), this example first
    :header: "Component", ":math:`\dot{E}_\mathrm{D}` [MW]", ":math:`\varepsilon` [%]", ":math:`c_\mathrm{F}` [USD/GJ]", ":math:`c_\mathrm{P}` [USD/GJ]", ":math:`\dot{C}_\mathrm{D}` [USD/h]", ":math:`f` [%]", ":math:`r` [%]"
    :widths: 14 14 12 13 13 13 11 11

    "AC", "2.10 / 2.10", "92.9 / 93.1", "8.02 / 7.6", "9.27 / 8.8", "60.7 / 57.6", "48.4 / 49.8", "15.5 / 14.9"
    "APH", "2.56 / 2.82", "84.6 / 83.0", "6.87 / 7.0", "8.50 / 8.6", "63.3 / 70.7", "16.2 / 14.8", "23.8 / 24.0"
    "CC", "25.3 / 30.5", "69.9 / 66.8", "4.03 / 3.8", "6.14 / 5.8", "368 / 421", "1.2 / 1.0", "52.1 / 50.3"
    "EXP", "2.99 / 3.06", "95.2 / 95.2", "7.39 / 7.0", "8.02 / 7.5", "79.6 / 76.7", "37.7 / 38.6", "8.6 / 8.2"

The specific costs agree within about 6 % and the exergoeconomic factor within about 1.5 points. The
remaining differences come from the thermodynamic model rather than from the costing: Kelly follows
the paper and treats air and combustion gas as ideal gases with constant :math:`c_p`, while ExerPy
evaluates real fluid properties. That shows most clearly in the combustion chamber, whose exergy
destruction differs by 17 %, and it carries over into its cost of exergy destruction.


The reference reports nothing for the plant as a whole, so there is no row for it here. Its plant
does differ from this one at that level: both deliver the same product, but it burns 7 % more fuel
for it, 1.773 against 1.644 kg/s of methane.

The evaporator and the economizer are not in the table because the reference treats the heat
recovery steam generator as a single component, while the model here resolves it into two. Their
exergy destruction adds up to 6.50 MW against the 6.72 MW reported for the whole HRSG, but the fuel
of the economizer alone is not the fuel of the HRSG, so their specific costs are not comparable.

.. note::

    The reference costs each stream with a single specific cost on its total exergy, that is,
    without splitting the physical exergy into a thermal and a mechanical part. The comparison above
    therefore holds for that convention; see
    :ref:`Split Physical Exergy in Exergoeconomics <examples_split_physical_exergy_label>` for the
    same plant costed both ways and for how far each of the two lands from these published values.

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
