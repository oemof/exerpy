.. _examples_split_physical_exergy_label:

*********************************************
Split Physical Exergy in Exergoeconomics
*********************************************

The exergoeconomic analysis runs with and without split physical exergy. With
:code:`split_physical_exergy=True` a material stream carries a cost rate for its thermal
(:math:`\dot{C}^\mathrm{T}`) and one for its mechanical exergy (:math:`\dot{C}^\mathrm{M}`); with
:code:`False` it carries a single cost rate for its physical exergy (:math:`\dot{C}^\mathrm{PH}`).
Both give a closed cost balance, but not the same cost of the product of a component.

This example analyses the :ref:`CGAM process <examples_cgam_exergoeconomic_label>` twice, with the
same component investment costs and the same boundary stream costs, and compares the two. The costs
are the ones of the CGAM problem itself :cite:`Valero1994`; see :ref:`the cost basis
<cgam_cost_basis>` for how they are obtained and how they compare with the paper.

.. note::

    Models that cannot provide the split, such as the ones exported from Aspen Plus, are analysed
    with :code:`split_physical_exergy=False`. Where the split is available, it is the more
    informative of the two, and below the ambient temperature it is the only one that credits the
    cold exergy of a stream to the product of the component producing it.

1. **The same specification for both runs**

The model, the fuel, product and loss definitions and the cost dictionary do not depend on the
split:

.. literalinclude:: /../examples/exergoeconomic_analysis/cgam/cgam_split_comparison.py
    :language: python
    :start-after: [setup]
    :end-before: [run_both]

2. **Run the analysis twice**

Only the :code:`split_physical_exergy` argument of the exergy analysis differs. The
:class:`~exerpy.analyses.ExergoeconomicAnalysis` takes the setting from the exergy analysis it is
built on, so nothing else has to be changed:

.. literalinclude:: /../examples/exergoeconomic_analysis/cgam/cgam_split_comparison.py
    :language: python
    :start-after: [run_both]
    :end-before: [compare_components]

3. **Component results**

.. literalinclude:: /../examples/exergoeconomic_analysis/cgam/cgam_split_comparison.py
    :language: python
    :start-after: [compare_components]
    :end-before: [compare_connections]

.. csv-table:: Component results of the CGAM process, specific costs in USD/GJ, cost rates in USD/h
    :header: "Component", ":math:`\\dot{E}_\\mathrm{D}` [kW]", ":math:`c_\\mathrm{F}` split", ":math:`c_\\mathrm{F}` no split", ":math:`c_\\mathrm{P}` split", ":math:`c_\\mathrm{P}` no split", ":math:`\\dot{C}_\\mathrm{D}` split", ":math:`\\dot{C}_\\mathrm{D}` no split", "dev. :math:`c_\\mathrm{P}` [%]"
    :widths: 12 10 10 10 10 10 10 10 10

    "CC", "25314.3", "4.033", "3.883", "6.133", "5.931", "367.52", "353.85", "-3.29"
    "AC", "2100.5", "7.985", "7.770", "9.156", "8.927", "60.38", "58.75", "-2.50"
    "GEN", "0.0", "7.985", "7.770", "7.985", "7.770", "0.00", "0.00", "-2.69"
    "APH", "2559.6", "6.844", "7.138", "8.465", "8.866", "63.07", "65.77", "4.74"
    "EV", "4586.8", "6.784", "7.138", "10.383", "10.904", "112.02", "117.87", "5.01"
    "PH", "1911.4", "14.719", "15.301", "n/a", "n/a", "101.28", "105.29", "n/a"
    "EXP", "2994.1", "7.344", "7.138", "7.985", "7.770", "79.16", "76.94", "-2.69"

The exergy destruction of every component is the same in both runs, so the exergy analysis itself
does not change. What changes is the cost charged to it, and it changes for two different reasons.

**The definition of fuel and product changes.** In the air preheater the split separates the
pressure loss of the cold stream from its temperature rise:

.. math::

    \text{split:} \quad
    \dot{E}_\mathrm{P} = \dot{E}^\mathrm{T}_\mathrm{out,c} - \dot{E}^\mathrm{T}_\mathrm{in,c}
    \qquad
    \dot{E}_\mathrm{F} = \dot{E}^\mathrm{PH}_\mathrm{in,h} - \dot{E}^\mathrm{PH}_\mathrm{out,h}
    + \bigl(\dot{E}^\mathrm{M}_\mathrm{in,c} - \dot{E}^\mathrm{M}_\mathrm{out,c}\bigr)

.. math::

    \text{no split:} \quad
    \dot{E}_\mathrm{P} = \dot{E}^\mathrm{PH}_\mathrm{out,c} - \dot{E}^\mathrm{PH}_\mathrm{in,c}
    \qquad
    \dot{E}_\mathrm{F} = \dot{E}^\mathrm{PH}_\mathrm{in,h} - \dot{E}^\mathrm{PH}_\mathrm{out,h}

Without the split the pressure loss of the air, 398 kW, is no longer charged as fuel; it is netted
against the temperature rise inside the product instead. Fuel and product both shrink by that
amount, the exergy destruction stays the same, and the product becomes 4.7 % more expensive because
the same cost is carried by less product.

**The cost of the inlet streams changes.** The evaporator and the gas turbine have the same fuel and
the same product in both runs, and their specific costs still differ. With the split, the auxiliary
equations price the thermal and the mechanical exergy of a stream separately, and the exhaust gas
leaving a component has a different mix of the two than the stream entering it. The cost that leaves
with the exhaust gas is therefore not the same, and neither is the cost charged to the shaft power
or to the steam.

4. **Cost of the material streams**

.. literalinclude:: /../examples/exergoeconomic_analysis/cgam/cgam_split_comparison.py
    :language: python
    :start-after: [compare_connections]
    :end-before: [system]

.. csv-table:: Specific cost of the material streams, :math:`c^\mathrm{TOT}` in USD/GJ
    :header: "Connection", ":math:`\\dot{E}` [kW]", "split", "no split", "deviation [%]"
    :widths: 14 14 14 14 14

    "1", "-39.3", "0.000", "0.000", "n/a"
    "10", "85120.4", "3.864", "3.864", "0.00"
    "2", "27519.9", "9.169", "8.940", "-2.50"
    "3", "41223.0", "8.928", "8.915", "-0.15"
    "4", "101029.0", "7.109", "7.111", "0.03"
    "5", "38375.2", "6.724", "7.066", "5.09"
    "6", "22112.5", "6.678", "7.014", "5.03"
    "6P", "6958.0", "6.447", "6.743", "4.59"
    "7", "2860.6", "5.846", "6.178", "5.67"
    "8", "61.6", "0.000", "0.000", "n/a"
    "8P", "2247.6", "0.000", "0.000", "n/a"
    "9", "12815.3", "8.953", "9.404", "5.04"

The boundary streams keep the cost they were given, and the deviation grows along the flue gas path:
streams 5, 6, 6P and 7 are between 4.6 % and 5.7 % more expensive without the split, and the steam
produced from them, stream 9, follows at 5.0 %.

5. **The system itself is not affected**

.. literalinclude:: /../examples/exergoeconomic_analysis/cgam/cgam_split_comparison.py
    :language: python
    :start-after: [system]
    :end-before: [end]

.. csv-table:: System costs in USD/h
    :header: "", "split", "no split"
    :widths: 20 20 20

    ":math:`\\dot{C}_\\mathrm{F}`", "1183.91", "1183.91"
    ":math:`\\dot{C}_\\mathrm{P}`", "1317.57", "1317.57"
    ":math:`\\dot{Z}`", "133.66", "133.66"

The cost entering the plant and the cost leaving it with the product are the same either way, and
both match the cost rate of the paper for this operating point. The split does not create or destroy
cost, it distributes the cost inside the plant differently, which is exactly what matters when
components are ranked against each other for an improvement.

.. note::

    Because the two definitions give different specific costs, results of the two modes should not
    be mixed within one study, and a comparison with literature values has to use the same setting
    the reference did. The CGAM paper reports no specific costs per component, only the purchase
    costs and the total cost rate of its optimal design, so it does not settle which of the two
    conventions a later comparison should use.
