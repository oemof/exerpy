.. _examples_cgam_exergoeconomic_label:

**************************************
CGAM Process (Exergoeconomic Analysis)
**************************************

.. seealso::

    The method behind this example: :ref:`Exergoeconomic Analysis <exergoeconomic_analysis_label>`.

This example performs the exergoeconomic analysis of the CGAM process. The plant is the base case
of the CGAM problem of Valero et al. :cite:`Valero1994`, modelled as in the :ref:`exergy analysis
example <examples_cgam_label>`, and the investment cost rates and the cost of the fuel follow the
cost model of the same paper, see :ref:`the cost basis <cgam_cost_basis>`.

.. note::

    This tutorial builds upon the :ref:`CGAM Process exergy analysis example <examples_cgam_label>` and uses
    data imported from a previously saved JSON file. Make sure you understand how to set up an exergy analysis
    from JSON data before proceeding.


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
the purchased equipment costs of its components. The cost rates used here follow from that cost
model for this base case; Kelly :cite:`Kelly2008` uses the same ones. Both works turn a purchased
equipment cost into a cost rate the same way,

.. math::

    \dot{Z}_i = \mathrm{PEC}_i \, \frac{\mathrm{CRF} \cdot \varphi}{N}

where :math:`\mathrm{CRF} = 0.182` is the annual capital recovery factor, :math:`\varphi = 1.06`
the maintenance factor, which adds the operation and maintenance expenses as a flat surcharge on
the capital cost, and :math:`N = 8000\,\mathrm{h/yr}` the operating hours per year. Note that the
purchased equipment cost is annualized directly: it is not scaled up to a total capital investment
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
the model has an evaporator and an economizer as separate components. It is split between the two in
the ratio of the purchased equipment costs of their sections, 67.8 % to 32.2 %, which follows from
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

**How to read the tables.** The plant converts fuel at 3.862 USD/GJ into a product at
8.581 USD/GJ. The exergoeconomic factor :math:`f = \dot{Z} / (\dot{Z} + \dot{C}_\mathrm{D})` tells which part
dominates the total cost rate of a component. Following Bejan et al. :cite:`Bejan1996`, a low
:math:`f` points to improving the efficiency of the component, even at a higher investment, and a
high :math:`f` to reducing its investment, even at some loss of efficiency. Here the combustion chamber has the largest cost rate of exergy destruction, 367.67 USD/h,
at :math:`f = 1.2` %, so its total cost rate is almost entirely the cost of its exergy destruction.
The compressor and the gas turbine have :math:`f` between 38 and 48 %, so the investment accounts for a
large share of their total cost rate.

.. _cgam_literature:

**Relation to the literature**

Kelly :cite:`Kelly2008` uses the same investment cost rates, but the results of the two works
are not comparable. The thesis does not state its thermodynamic model, and its stream data do not
follow from that of the CGAM problem, ideal gases with constant specific heats :cite:`Valero1994`.
Its plant also operates at a different point: it burns 1.773 kg/s of methane for the same product,
compared with 1.644 kg/s here. The results are therefore shown as they are, without a comparison with the
published values.

The :code:`evaluate_results()` method ranks components by their total cost rate
(:math:`\dot{C}_\mathrm{D} + \dot{Z}`) to identify the most promising targets for optimization.
You can sort by different criteria using the :code:`sort_by` parameter:

.. code-block:: python

    # Sort by cost of exergy destruction only
    eco.evaluate_results(sort_by="C_D", top_n=3)

    # Sort by exergoeconomic factor
    eco.evaluate_results(sort_by="f", top_n=3)


.. seealso::

    The same model is analysed with and without split physical exergy in
    :ref:`Split Physical Exergy in Exergoeconomics <examples_split_physical_exergy_label>`.

Full code
=========

.. dropdown:: Full code of this example

    .. literalinclude:: /../examples/exergoeconomic_analysis/cgam/cgam_exergoeconomic.py
        :language: python
