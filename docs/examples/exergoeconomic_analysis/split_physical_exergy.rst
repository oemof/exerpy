.. _examples_split_physical_exergy_label:

*********************************************
Split Physical Exergy in Exergoeconomics
*********************************************

.. seealso::

    The method behind this example: :ref:`Exergoeconomic Analysis <exergoeconomic_analysis_label>`.

The exergoeconomic analysis runs with and without split physical exergy. With
:code:`split_physical_exergy=True` a material stream carries a cost rate for its thermal
(:math:`\dot{C}^\mathrm{T}`) and one for its mechanical exergy (:math:`\dot{C}^\mathrm{M}`); with
:code:`False` it carries a single cost rate for its physical exergy (:math:`\dot{C}^\mathrm{PH}`).
Both give a closed cost balance, but not the same cost of the product of a component.

This example analyses the :ref:`CGAM process <examples_cgam_exergoeconomic_label>` twice, with the
same component investment costs and the same boundary stream costs, and compares the two. The plant
and the costs follow the CGAM problem :cite:`Valero1994`; see :ref:`the cost basis
<cgam_cost_basis>` for how the costs are obtained.

.. note::

    Models that cannot provide the split, such as the ones exported from Aspen Plus, are analysed
    with :code:`split_physical_exergy=False`. Where the split is available, it is the more
    informative of the two, and below the ambient temperature it is the only one that credits the
    cold exergy of a stream to the product of the component producing it.

The flowsheet below names the components and the streams used throughout this example.

.. figure:: /_static/images/flowsheets/cgam.svg
    :align: center
    :alt: CGAM flowsheet
    :figclass: only-light

    Figure: Flowsheet of the CGAM process

.. figure:: /_static/images/flowsheets/cgam_darkmode.svg
    :align: center
    :alt: CGAM flowsheet
    :figclass: only-dark

    Figure: Flowsheet of the CGAM process

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
    :end-before: [system]

.. csv-table:: Cost rates of the components in USD/h
    :header: "Component", ":math:`\dot{C}_\mathrm{F}` split", ":math:`\dot{C}_\mathrm{F}` no split", ":math:`\dot{C}_\mathrm{P}` split", ":math:`\dot{C}_\mathrm{P}` no split", ":math:`\dot{C}_\mathrm{D}` split", ":math:`\dot{C}_\mathrm{D}` no split", ":math:`\dot{Z}`", ":math:`\dot{C}_\mathrm{D}+\dot{Z}` split", ":math:`\dot{C}_\mathrm{D}+\dot{Z}` no split"
    :widths: 12 10 10 10 10 10 10 8 10 10

    "CC", "1220.96", "1175.07", "1297.55", "1254.47", "367.67", "353.85", "4.40", "372.07", "358.25"
    "AC", "856.59", "832.74", "919.57", "895.95", "60.66", "58.97", "56.99", "117.65", "115.96"
    "GEN", "866.41", "842.29", "866.41", "842.29", "0.00", "0.00", "0.00", "0.00", "0.00"
    "APH", "411.94", "419.97", "431.50", "439.82", "63.29", "66.10", "12.26", "75.55", "78.36"
    "EV", "371.29", "391.36", "395.84", "416.42", "112.38", "118.45", "11.48", "123.85", "129.93"
    "PH", "101.65", "105.81", "n/a", "n/a", "101.65", "105.81", "5.45", "107.10", "111.26"
    "EXP", "1666.30", "1617.99", "1723.00", "1675.02", "79.63", "77.32", "48.16", "127.79", "125.48"
    "TOT", "1183.91", "1183.91", "1322.65", "1322.65", "548.78", "548.78", "138.74", "687.52", "687.52"

.. csv-table:: Specific costs in USD/GJ and exergoeconomic indicators in %
    :header: "Component", ":math:`c_\mathrm{F}` split", ":math:`c_\mathrm{F}` no split", ":math:`c_\mathrm{P}` split", ":math:`c_\mathrm{P}` no split", ":math:`f` split", ":math:`f` no split", ":math:`r` split", ":math:`r` no split"
    :widths: 12 11 11 11 11 11 11 11 11

    "CC", "4.034", "3.883", "6.135", "5.931", "1.183", "1.228", "52.065", "52.757"
    "AC", "8.022", "7.799", "9.269", "9.031", "48.439", "49.145", "15.535", "15.791"
    "GEN", "8.022", "7.799", "8.022", "7.799", "0.000", "0.000", "0.000", "0.000"
    "APH", "6.868", "7.173", "8.500", "8.916", "16.228", "15.646", "23.762", "24.286"
    "EV", "6.806", "7.173", "10.405", "10.946", "9.266", "8.833", "52.889", "52.589"
    "PH", "14.773", "15.377", "n/a", "n/a", "5.092", "4.902", "n/a", "n/a"
    "EXP", "7.388", "7.173", "8.022", "7.799", "37.687", "38.380", "8.592", "8.720"
    "TOT", "3.862", "3.862", "8.581", "8.581", "20.180", "20.180", "122.165", "122.165"

The investment cost :math:`\dot{Z}` is an input and identical in both runs, and so is the exergy
destruction of every component: the exergy analysis itself does not change. The ``TOT`` row refers to the
whole plant. Its cost of exergy destruction is the exergy destroyed in the plant at the specific
cost of the fuel of the plant, :math:`\dot{C}_\mathrm{D,tot} = c_\mathrm{F,tot} \, \dot{E}_\mathrm{D,tot}`,
not the sum of the :math:`\dot{C}_{\mathrm{D},k}` of the components, so the whole row is the same in
both runs. What changes is the cost charged to the exergy destruction of each component, and it
changes for two different reasons.

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
the same product in both runs, but their specific costs still differ. With the split, the auxiliary
equations price the thermal and the mechanical exergy of a stream separately, and the exhaust gas
leaving a component has a different mix of the two than the stream entering it. The cost that leaves
with the exhaust gas is therefore not the same, which is why the deviation grows along the flue gas
path and reaches about 5 % in the components at its end, the evaporator and the economizer.

Together the two effects change the order in which the components would be addressed for
improvement. Ranked by :math:`\dot{C}_\mathrm{D} + \dot{Z}`, the combustion chamber leads in both
runs by a wide margin, but the second and third places change hands: with the split the gas turbine
comes before the evaporator (127.79 versus 123.85 USD/h); without it the evaporator comes before
the gas turbine (129.93 versus 125.48 USD/h).

4. **The system itself is not affected**

.. literalinclude:: /../examples/exergoeconomic_analysis/cgam/cgam_split_comparison.py
    :language: python
    :start-after: [system]
    :end-before: [end]

.. csv-table:: System costs in USD/h
    :header: "", "split", "no split"
    :widths: 20 20 20

    ":math:`\dot{C}_\mathrm{F}`", "1183.91", "1183.91"
    ":math:`\dot{C}_\mathrm{P}`", "1322.65", "1322.65"
    ":math:`\dot{Z}`", "138.74", "138.74"

The cost entering the plant and the cost leaving it with the product are the same either way. The
split does not create or destroy cost; it distributes the cost inside the plant differently, which is
exactly what matters when components are ranked against each other for improvement.

5. **Which convention the published results use**

Kelly :cite:`Kelly2008`, who uses the same investment costs as this example, assigns each stream a single
specific cost for its total exergy, that is, without splitting the physical exergy. Her results are
not compared with the ones above, because her plant model and operating point differ from those
used here (see :ref:`the CGAM example <cgam_literature>`).

.. note::

    Because the two definitions give different specific costs, results of the two modes should not be
    mixed within one study, and a comparison with literature values has to use the same setting as the
    reference.

Full code
=========

.. dropdown:: Full code of this example

    .. literalinclude:: /../examples/exergoeconomic_analysis/cgam/cgam_split_comparison.py
        :language: python
