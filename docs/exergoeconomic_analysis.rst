.. _exergoeconomic_analysis_label:

#######################
Exergoeconomic Analysis
#######################

Exergoeconomic analysis provides a systematic methodology to quantify both the thermodynamic performance and
the associated economic costs of energy‐conversion systems. Building upon exergy analysis, which accounts for
irreversibilities and the quality of energy, exergoeconomics introduces cost formulation rules to allocate
monetary values to all exergy streams entering and leaving each component :cite:`Bejan1996`. This approach enables the
identification of cost‐intensive inefficiencies, guiding optimal design and operation decisions to minimize
total exergy consumption and expenses. The theory described in this section follows the Specific Exergy Costing
(SPECO) method as presented by Lazzaretto and Tsatsaronis (2006) :cite:`lazzaretto2006speco`.

.. dropdown:: Where this step fits: step 5 of the workflow

    .. include:: /_workflow.rst

***************************************
Fundamentals of exergoeconomic analysis
***************************************

Exergoeconomic analysis couples the first and second laws of thermodynamics with cost accounting principles.
Each exergy stream—whether associated with material, work, or heat transfer—is assigned a cost rate, and
cost balances are formulated for every component.

In this framework, we define:

- :math:`\dot{C}_{i}` and :math:`\dot{C}_{e}` as the cost rates associated with exergy streams entering and exiting a component,
  respectively,
- :math:`\dot{C}_{w}` as the cost rate associated with work flow,
- :math:`\dot{C}_{q}` as the cost rate associated with heat transfer.

The component cost balance is :cite:`Bejan1996`:

  .. math::

      \sum_i \dot{C}_{i,k} + \dot{C}_{q,k} + \dot{Z}_k = \sum_e \dot{C}_{e,k} + \dot{C}_{w,k}

where :math:`\dot{Z}_k` represents the total charges due to capital investment and operating and maintenance costs.

Two fundamental principles govern the auxiliary costing equations :cite:`lazzaretto2006speco`:

- **F principle**: For each exergy removal from a fuel stream, the unit cost remains equal to the average cost
  at which that exergy was supplied by upstream components.
- **P principle**: All exergy added to product streams is assigned the same unit cost, denoted :math:`c_P`,
  determined from the component cost balance and the F equations.

Costs are assigned to exergy, :math:`\dot{C} = c \cdot \dot{E}` :cite:`lazzaretto2006speco`, so a stream without
exergy of a share :math:`x` (thermal, mechanical, physical or chemical) carries no cost of that share. Where an
auxiliary equation equates specific costs and one of the two streams has no exergy of the share, ExerPy writes
:math:`\dot{C}^{x}_\mathrm{out} = 0` instead, for the outlet without exergy, or for the outlet of the equation
if the inlet has none. An inlet is never fixed, since its cost is set upstream. In the mixing rule of a mixer or
deaerator, an inlet without exergy of the share adds nothing, and an outlet without it gets
:math:`\dot{C}^{x}_\mathrm{out} = 0`.

***********
Terminology
***********

The definitions and symbols used in exergoeconomic analysis are summarized below:

.. list-table:: Terminology
    :widths: 15 20 15 50
    :header-rows: 1
    :class: tight-table

    * - Variable
      - Name
      - Symbol
      - Description
    * - :code:`c_i`, :code:`C_i`
      - (specific) inlet cost
      - :math:`c_i`, :math:`\dot{C}_i`
      - (specific) cost flow rate of an entering exergy stream
    * - :code:`c_e`, :code:`C_e`
      - (specific) outlet cost
      - :math:`c_e`, :math:`\dot{C}_e`
      - (specific) cost flow rate of an exiting exergy stream
    * - :code:`c_w`, :code:`C_w`
      - (specific) work cost
      - :math:`c_w`, :math:`\dot{C}_w`
      - (specific) cost rate associated with work flow
    * - :code:`c_q`, :code:`C_q`
      - (specific) heat cost
      - :math:`c_q`, :math:`\dot{C}_q`
      - (specific) cost rate associated with heat transfer
    * - :code:`c_P`, :code:`C_P`
      - (specific) product cost
      - :math:`c_P`, :math:`\dot{C}_P`
      - (specific) cost rate of the product exergy stream
    * - :code:`c_F`, :code:`C_F`
      - (specific) fuel cost
      - :math:`c_F`, :math:`\dot{C}_F`
      - (specific) cost rate of the fuel exergy stream
    * - :code:`C_D`
      - cost of exergy destruction
      - :math:`\dot{C}_D`
      - cost rate associated with exergy destruction
    * - :code:`C_L`
      - cost of exergy loss
      - :math:`\dot{C}_L`
      - cost rate associated with exergy loss
    * - :code:`f`
      - exergoeconomic factor
      - :math:`f_k`
      - ratio of non-thermodynamic costs to total component cost
    * - :code:`r`
      - relative cost difference
      - :math:`r_k`
      - normalized increase of product over fuel unit cost
    * - :code:`Z`
      - charges
      - :math:`\dot{Z}`
      - sum of capital and O&M cost rates
    * - :code:`Z_diss`
      - charged dissipative cost
      - :math:`\dot{Z}_\mathrm{diss}`
      - share of the cost of the dissipative components charged to the component

.. note::

    The auxiliary costing equations derived from the F and P principles, together with the component cost
    balance, form a solvable linear system that yields the cost rates for all exergy streams in the system,
    see :ref:`How the equation system is built and solved <exergoeconomic_system_label>`.

.. _exergoeconomic_metrics_label:

*************************************
Exergoeconomic metrics and indicators
*************************************

After solving the SPECO equations for all cost rates, several exergoeconomic indicators are computed to assess
the economic impact of irreversibilities in each component. Three key metrics are:

- **Cost rate of exergy destruction**

The cost associated with thermodynamic inefficiencies in component *k* is

    .. math::

        \dot{C}_{\mathrm{D},k} = c_{\mathrm{F},k}\,\dot{E}_{\mathrm{D},k}

where :math:`c_{\mathrm{F},k}` is the specific cost of the fuel exergy of component *k* and
:math:`\dot{E}_{\mathrm{D},k}` its exergy destruction rate :cite:`Bejan1996`.

- **Exergoeconomic factor**

The fraction of a component’s total cost arising from investment and O&M (non-thermodynamic) charges is

    .. math::

        f_k = \frac{\dot{Z}_k}{\dot{Z}_k + \dot{C}_{\mathrm{D},k}}

with the investment and O&M cost rate :math:`\dot{Z}_k` of the component only :cite:`Bejan1996`. The share
:math:`\dot{Z}_{\mathrm{diss},k}` of the cost of the dissipative components that is charged to component *k*, in
proportion to its exergy destruction, enters its cost balance and thus its :math:`c_{\mathrm{P},k}` and
:math:`r_k` :cite:`lazzaretto2006speco`. It is not part of :math:`f_k`, since it is neither the investment of the
component nor the cost of its exergy destruction.

A high :math:`f_k` indicates that capital and O&M dominate the cost, suggesting a focus on reducing
:math:`\dot{Z}_k`. A low :math:`f_k` signals that inefficiencies (exergy destruction) are the primary cost drivers :cite:`Bejan1996`.

- **Relative cost difference**

The relative increase in specific cost from fuel to product exergy for component *k* is

    .. math::

        r_k = \frac{c_{\mathrm{P},k} - c_{\mathrm{F},k}}{c_{\mathrm{F},k}}

where :math:`c_{\mathrm{P},k}` and :math:`c_{\mathrm{F},k}` are the specific product and fuel costs. Lowering
:math:`r_k` through efficiency improvements is recommended for cost optimization :cite:`Bejan1996`.


.. _exergoeconomic_system_label:

*********************************************
How the equation system is built and solved
*********************************************

The cost rates of all streams follow from one linear equation system :math:`A\,\dot{C} = b`, with one
unknown per cost variable and one row per equation. ExerPy builds it from the analysed plant and the
cost dictionary, solves it and then derives the indicators of every component.

The cost variables
==================

Every stream that touches a component of the plant carries cost variables:

- a **material stream** one per share of its exergy: :math:`\dot{C}^\mathrm{T}` and
  :math:`\dot{C}^\mathrm{M}` with split physical exergy, :math:`\dot{C}^\mathrm{PH}` without it,
  and :math:`\dot{C}^\mathrm{CH}` in addition when chemical exergy is enabled;
- a **heat or power stream** one, :math:`\dot{C}^\mathrm{TOT}`;
- a **dissipative component** one more, the cost :math:`\dot{C}_\mathrm{diff}` of the exergy it
  destroys without a product, and a **storage** one for the exergy it puts into or takes out of its
  store.

The equations
=============

.. list-table:: The rows of the equation system
    :widths: 22 30 48
    :header-rows: 1
    :class: tight-table

    * - Kind
      - Rows
      - What the row states
    * - ``cost_balance``
      - one per component with a cost balance
      - :math:`\sum \dot{C}_\mathrm{in} - \sum \dot{C}_\mathrm{out} = -\dot{Z}`; the splitter, the
        power bus, the cycle closer, the storage and dissipative components have none
    * - ``boundary``
      - one per cost variable of every material or heat stream entering the plant, and of every
        power stream entering it with a given cost
      - the cost given in the cost dictionary, :math:`\dot{C} = c\,\dot{E}`; a material stream gets the
        same specific cost for each of its shares
    * - ``aux_power_eq``
      - one less than the number of power streams entering the plant
      - all purchased power has the same specific cost
    * - ``aux_f_rule``, ``aux_f_rule_hot``, ``aux_f_rule_cold``
      - written by the components
      - F principle: exergy removed from a stream leaves at the specific cost it entered with
    * - ``aux_p_rule``
      - written by the components
      - P principle: every exergy added to the products of a component has the same specific cost
    * - ``aux_equality``
      - written by the components
      - a share that only passes through keeps its specific cost, for example the chemical exergy
        through a component without a reaction
    * - ``aux_mixing``
      - written by mixer, deaerator and combustion chamber
      - the rules of a component that mixes streams, for the shares its cost balance does not cover
    * - ``dis_equality``, ``dis_balance``
      - written by dissipative components
      - the main working fluid keeps its specific cost, the auxiliary fluid, such as cooling water,
        leaves without cost, and the cost of the destroyed exergy and of the auxiliary fluid,
        :math:`\dot{C}_\mathrm{diff}`, is charged to the productive components in proportion to their
        exergy destruction :cite:`lazzaretto2006speco`

The system is square by construction. A component with a cost balance writes one auxiliary row per
cost variable of its outlets, less one, since its cost balance determines the last one; a dissipative
component writes one row more and has no cost balance. Every stream inside the plant is the outlet of
exactly one component, and every stream entering the plant gets its boundary rows, so the number of
rows equals the number of cost variables. For the CGAM process with chemical exergy, for example:

.. list-table:: The equation system of the CGAM process
    :widths: 40 30 30
    :header-rows: 1
    :class: tight-table

    * -
      - split physical exergy
      - without the split
    * - material streams × cost variables
      - 12 × 3 (T, M, CH)
      - 12 × 2 (PH, CH)
    * - heat and power streams
      - 3
      - 3
    * - dissipative component
      - 0
      - 0
    * - **cost variables and rows**
      - **39**
      - **27**
    * - of which cost balances, boundary rows, auxiliary rows
      - 7, 9, 23
      - 7, 6, 14

The variables and the rows of a run can be listed by name:

.. code-block:: python

    eco.run(costs)
    eco.print_variables()   # {0: "C_1_PH", 1: "C_1_CH", 2: "C_10_PH", ...}
    eco.print_equations()   # {0: {"kind": "cost_balance", "object": ["CC"], ...}, ...}

Solving
=======

:meth:`~exerpy.analyses.ExergoeconomicAnalysis.run` solves the system with ``numpy.linalg.solve``
and then

1. charges the cost of the exergy destroyed in dissipative components to the productive ones;
2. assigns every stream its cost rates and specific costs, :math:`c = \dot{C}/\dot{E}` per share,
   and with the split :math:`\dot{C}^\mathrm{PH} = \dot{C}^\mathrm{T} + \dot{C}^\mathrm{M}`;
3. computes :math:`\dot{C}_\mathrm{F}`, :math:`\dot{C}_\mathrm{P}`, :math:`\dot{C}_\mathrm{D}`,
   :math:`r` and :math:`f` of every component;
4. checks the cost balance of every component and warns where one is not closed;
5. charges the cost of the loss streams to the product streams, in proportion to their net exergy
   (Bejan et al., Example 8.1) :cite:`Bejan1996`. A stream subtracted in ``E_P``, such as the
   feedwater of a boiler, is paired with the product stream it turns into downstream, such as the
   steam. If it reaches no product stream or more than one, the gross exergy of the products is used
   and a warning names the stream;
6. checks the cost balance of the whole plant,
   :math:`\dot{C}_\mathrm{P,tot} = \dot{C}_\mathrm{F,tot} + \sum \dot{Z}`, and raises an error where
   it is not closed.

What changes with the split of the physical exergy
==================================================

With ``split_physical_exergy=True``, the thermal and the mechanical exergy of a stream are costed
separately; without it, the physical exergy is costed as a whole.

- **Variables:** a material stream has :math:`\dot{C}^\mathrm{T}` and :math:`\dot{C}^\mathrm{M}`
  instead of :math:`\dot{C}^\mathrm{PH}`, so the system has one variable more per stream, 39 instead
  of 27 for the CGAM process.
- **Rules:** with the split, a component writes a rule for each share. A heat exchanger, for
  example, follows the F principle for the thermal exergy its hot stream gives off, while the
  mechanical exergy passes at its own specific cost. Without the split, the rules for the mechanical
  exergy fall away and the thermal rules apply to the physical exergy instead.
- **Results:** the split lets the two shares of a stream carry different specific costs. A pump, for
  example, adds mechanical exergy at the cost of its product, while the thermal exergy of the stream
  keeps the cost it had. Without the split, both are averaged into one specific cost. The cost
  balances are met either way, but the specific costs of streams and components differ, see
  :ref:`Split Physical Exergy in Exergoeconomics <examples_split_physical_exergy_label>`.
- **Below the ambient temperature** only the split credits the cold exergy of a stream to the product
  of the component that produces it. Models whose streams lack the thermal and mechanical shares,
  such as a JSON input with the physical exergy only, are analysed without it.

*************************************************
Getting started with exergoeconomic analysis
*************************************************

Prerequisites
=============

Before performing an exergoeconomic analysis, you need:

1. A completed exergy analysis
2. Component investment cost rates and specific costs of the input streams, given directly or obtained
   from the purchased equipment costs with the :ref:`economic analysis <economic_analysis_label>`,
   whose :meth:`~exerpy.analyses.EconomicAnalysis.compute_costs` returns them in the format below

Every component of ExerPy takes part in the exergoeconomic analysis. Two of them need an input that
the thermodynamic model does not carry:

- a combustion chamber needs the chemical exergy, so the exergy analysis has to run with a
  ``chemExLib``;
- a steam generator needs the temperature of its heat source in its ``T_hot`` attribute, since that
  source is usually outside the model.

A simple heat exchanger may be given the temperature of its heat source or its heat consumer as
well, see :ref:`Heat from or to outside the model <heat_boundary_label>`.

.. note::

    With :code:`split_physical_exergy=True`, the cost of a material stream is allocated to its
    thermal and its mechanical exergy separately; with :code:`False`, it is allocated to its physical
    exergy as a whole. Both are supported, so models whose streams lack the thermal and mechanical
    shares can be analysed as well. The two conventions do not give the same specific
    costs; see :ref:`What changes with the split <exergoeconomic_system_label>` and
    :ref:`Split Physical Exergy in Exergoeconomics <examples_split_physical_exergy_label>`.

Workflow overview
=================

The exergoeconomic analysis in ExerPy follows four steps:

1. **Perform the exergy analysis**, here with the physical exergy split:

.. code-block:: python

    from exerpy import ExergyAnalysis, ExergoeconomicAnalysis

    ean = ExergyAnalysis.from_json(model_path, chemExLib="Ahrendts", split_physical_exergy=True)

    fuel = {"inputs": ["1", "10"], "outputs": []}
    product = {"inputs": ["E1", "9"], "outputs": ["8"]}
    loss = {"inputs": ["7"], "outputs": []}

    ean.analyse(E_F=fuel, E_P=product, E_L=loss)

2. **Create the exergoeconomic analysis** instance:

.. code-block:: python

    eco = ExergoeconomicAnalysis(ean)

3. **Define costs and run** the analysis:

.. code-block:: python

    costs = {
        # Component investment cost rates [EUR/h]
        "AC_Z": 80,
        "CC_Z": 30,
        "EXP_Z": 100,
        "GEN_Z": 40,
        # Input stream specific costs [EUR/GJ]
        "1_c": 0.0,    # Ambient air (free)
        "10_c": 10.0,   # Natural gas fuel
        "8_c": 0.5,     # Feedwater
    }

    eco.run(costs)

The cost rates :math:`\dot{Z}` and the specific costs of the entering streams can be typed in, as
above, or derived with the :ref:`economic analysis <economic_analysis_label>`: the purchased
equipment costs come from one of the :ref:`four sources <purchase_equipment_costs_label>` (known
costs, scaled costs of reference components, user-defined cost equations or the correlations of
OpenPyTEA), the total revenue requirement method turns them into :math:`\dot{Z}`, and
:meth:`~exerpy.analyses.EconomicAnalysis.compute_costs` returns both in the format of the cost
dictionary:

.. code-block:: python

    from exerpy import EconomicAnalysis

    economic = EconomicAnalysis(
        PEC={
            "AC": 1.2e6,
            "CC": 4.0e5,
            # ... the other components
        },
        fuel_costs={"1": 0.0, "10": 10.0, "8": 0.5},   # EUR/GJ, the streams entering the plant
        # ... reference_year, base_year, cost_index and the parameters, see Economic Analysis
    )
    eco.run(economic.compute_costs(ean))   # the "_Z" and "_c" entries of the cost dictionary

:ref:`From Equipment Costs to the Cost of the Product <examples_heatpump_exergoeconomic_label>` shows
the whole way on a heat pump.

4. **View results**:

.. code-block:: python

    eco.exergoeconomic_results()
    eco.evaluate_results()

.. _exergoeconomic_cost_input_label:

Cost input format
=================

The cost dictionary passed to :code:`run()` requires two types of entries:

.. list-table:: Cost dictionary format
    :widths: 25 20 15 40
    :header-rows: 1
    :class: tight-table

    * - Key format
      - Type
      - Unit
      - Description
    * - :code:`"<component_name>_Z"`
      - Component cost
      - currency/h
      - Investment and O&M cost rate for each component
    * - :code:`"<connection_name>_c"`
      - Stream cost
      - currency/GJ
      - Specific cost for each input stream crossing the system boundary

A value can also be given in another unit, as long as it is in the currency of the analysis, e.g.
:code:`"10_c": 90.0, "10_c_unit": "EUR / MWh"` or :code:`"COMP_Z": 0.0222, "COMP_Z_unit": "EUR / s"`.
A cost per day or per year is not accepted: turning it into a cost per hour of operation needs the
operating hours, which :class:`~exerpy.analyses.EconomicAnalysis` takes into account.

A material stream entering the plant can also have a cost for each form of its exergy. In the SPECO
method, the cost rate of each exergy form (thermal, mechanical and chemical) of a material stream
supplied to the plant from outside is a known value of its own :cite:`lazzaretto2006speco`. The keys
are :code:`"<connection_name>_c_T"`, :code:`"<connection_name>_c_M"` and
:code:`"<connection_name>_c_CH"`, and :code:`"<connection_name>_c_PH"` stands for the thermal and the
mechanical exergy together. Without the split of the physical exergy only :code:`"_c_PH"` and
:code:`"_c_CH"` apply. :code:`"_c_CH"` is used only when the chemical exergy is part of the analysis.
A form without a cost of its own takes the :code:`"_c"` of the stream, and each key can have its own
unit, e.g. :code:`"10_c_CH_unit"`.

**Mandatory costs:**

- All components must have a :code:`_Z` cost, except the :code:`CycleCloser`, the :code:`PowerBus`
  and the :code:`Splitter`. These pass their streams on without a cost balance of their own, so a
  cost given for one of them could not be charged to any stream and is rejected.
- All material and power/heat streams entering the system boundary must have a :code:`_c` cost.
  A material stream can have a cost for each of its exergy forms instead. For heat, what counts is
  the direction of its exergy, which below the ambient temperature is against the heat: heat that
  cools a stream below it (a chiller) needs a cost, heat taken in by such a stream (an evaporator)
  is priced by the component and needs none.

**Examples:**

- :code:`"COMP_Z": 80.0` — compressor investment cost of 80 EUR/h
- :code:`"1_c": 0.0` — ambient air enters the system at zero cost
- :code:`"10_c": 25.0` — natural gas enters the system at 25 EUR/GJ
- :code:`"10_c": 2.0, "10_c_CH": 10.0` — the chemical exergy of stream 10 costs 10 EUR/GJ, its
  thermal and mechanical exergy 2 EUR/GJ


Interpreting results
====================

After running the analysis, use :code:`exergoeconomic_results()` to display the full results,
and :code:`evaluate_results()` to identify the components with the highest cost improvement potential.

.. code-block:: python

    # Display all results (4 DataFrames)
    df_comp, df_mat_props, df_mat_costs, df_non_mat = eco.exergoeconomic_results()

    # Identify top components for optimization
    eco.evaluate_results(sort_by="C_D+Z", top_n=5)

The component results table lists the cost rates and the indicators defined in
:ref:`Exergoeconomic metrics and indicators <exergoeconomic_metrics_label>`. The components with the
largest total cost rate :math:`\dot{C}_\mathrm{D} + \dot{Z}` are the most promising targets for an
improvement. The column :code:`Z` holds the given cost rate of a component and :code:`Z_diss` the share
of the cost of the dissipative components charged to it. :code:`C_D+Z` and :code:`f` leave
:code:`Z_diss` out, since :code:`C_D+Z` of the dissipative component already contains it. In the row
:code:`TOT`, :code:`Z` is the sum of the given cost rates only, since the charged shares stay inside the
plant, and :code:`C_D` is :math:`c_\mathrm{F,tot}\,\dot{E}_\mathrm{D,tot}`, not the sum of the column,
since the cost of the exergy destruction of the plant cannot be found by adding the costs of the
components :cite:`Bejan1996`.

The :code:`evaluate_results()` method accepts the following :code:`sort_by` options:
:code:`"C_D+Z"` (default), :code:`"C_D"`, :code:`"Z"`, :code:`"r"`, :code:`"f"`.

To verify the integrity of the solution, use :code:`check_cost_balance()`:

.. code-block:: python

    balances = eco.check_cost_balance(tol=1e-3)
    for name, (residual, is_balanced) in balances.items():
        print(f"{name}: residual={residual:.6f}, balanced={is_balanced}")

.. note::

    Results depend on the auxiliary equations, and those are a modelling choice. Check the cost
    balance of every component with
    :meth:`~exerpy.analyses.ExergoeconomicAnalysis.check_cost_balance` and validate the results
    independently before basing a decision on them.

Troubleshooting
===============

The messages below point to what is missing or wrong in the specification.

**"Cost for component '...'" or "Cost for input connection '...' is mandatory but not provided"**

A :code:`"<name>_Z"` or :code:`"<name>_c"` entry is missing; :ref:`Cost input format
<exergoeconomic_cost_input_label>` lists which components and streams need one. A stream entering
free of charge is given :code:`0.0`.

**"Exergoeconomic system is singular (rank r/n)"**

The rows do not determine all cost variables. ExerPy prints a dependency report, which can also be
called directly with :meth:`~exerpy.analyses.ExergoeconomicAnalysis.print_dependency_report`. Read it
as follows:

- *Equations with no variables* are rows that stayed empty: the system has fewer equations than
  cost variables. Look for warnings of the components at the start of the run, such as "not
  implemented" for a case a component does not cover or "No auxiliary equations provided". A power
  stream entering the plant without a cost, in a plant that exports no power,
  leaves a row empty as well; give it a :code:`"<name>_c"`.
- *Variables never used* are cost variables no row contains: a stream between components that have
  no cost balance, for example.
- *Exactly collinear pairs* are two rows that state the same thing, for example two conditions on
  the same stream.
- *SVD dependencies* list a group of rows that together are dependent. The components and streams
  named in these rows are where a rule is missing or doubled.

``run(costs, allow_singular=True)`` returns a least-squares solution instead of an error. It is not
unique and may not be physically consistent; use it to inspect the system, not as a result.

**"Exergoeconomic cost balance of the entire system is not satisfied"**

Fuel, product and loss of the plant do not cover every stream that crosses the system boundary. The
exergy analysis warns about such streams ("The following system boundary connections are not included
in E_F, E_P, or E_L"); add each of them to ``E_F``, ``E_P`` or ``E_L``.

**"Balance for component ... not fulfilled"**

The cost balance of a component is not closed after the solution, which points to a rule of that
component that contradicts its balance. Check it with
:meth:`~exerpy.analyses.ExergoeconomicAnalysis.check_cost_balance`.

**"The solution of the cost matrix contains NaN values"**

A stream carries no valid exergy value, for example a NaN in the export of the model. Check the
exergy of the streams in :meth:`~exerpy.analyses.ExergyAnalysis.exergy_results`.
