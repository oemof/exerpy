#######################
Exergoeconomic Analysis
#######################
.. warning::
    **Development Status: Beta**

    The exergoeconomic analysis functionality is currently in development and undergoing testing. 
    Methods, interfaces, and results may change in future versions. While we strive for accuracy, 
    users should validate results independently for critical applications. We welcome feedback and 
    bug reports to help improve this feature.

    In the actual implementation of the exergoeconomic analysis, the exergy of the material streams is split 
    into thermal, mechanical and chemical parts. Therefore, `split_physical_exergy` should be set to 
    `True`. This makes the exergoeconomic analysis not applicable to models simulated with Aspen. 
    For some components, such as combustion chambers, the chemical exergy is necessary as well. 

    
Exergoeconomic analysis provides a systematic methodology to quantify both the thermodynamic performance and
the associated economic costs of energy‐conversion systems. Building upon exergy analysis, which accounts for
irreversibilities and the quality of energy, exergoeconomics introduces cost formulation rules to allocate
monetary values to all exergy streams entering and leaving each component :cite:`Bejan1996`. This approach enables the
identification of cost‐intensive inefficiencies, guiding optimal design and operation decisions to minimize
total exergy consumption and expenses. The theory described in this section follows the Specific Exergy Costing
(SPECO) method as presented by Lazzaretto and Tsatsaronis (2006) :cite:`lazzaretto2006speco`.

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

The component cost balance :cite:`Bejan1996`:

  .. math::

      \sum_i \dot{C}_{i,k} + \dot{C}_{q,k} + \dot{Z}_k = \sum_e \dot{C}_{e,k} + \dot{C}_{w,k}

where :math:`Z_k` represents the total charges due to capital investment and operating & maintenance costs.

Two fundamental principles govern the auxiliary costing equations :cite:`lazzaretto2006speco`:

- **F principle**: For each exergy removal from a fuel stream, the unit cost remains equal to the average cost
  at which that exergy was supplied by upstream components.
- **P principle**: All exergy added to product streams is assigned the same unit cost, denoted :math:`c_P`,
  determined from the component cost balance and F equations.

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

.. note::

    The auxiliary costing equations derived from the F and P principles, together with the component cost
    balance, form a solvable linear system that yields the cost rates for all exergy streams in the system.

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

A high :math:`f_k` indicates that capital and O&M dominate the cost, suggesting focus on reducing
:math:`\dot{Z}_k`. A low :math:`f_k` signals that inefficiencies (exergy destruction) are the primary cost drivers :cite:`Bejan1996`.

- **Relative cost difference**

The relative increase in specific cost from fuel to product exergy for component *k* is

    .. math::

        r_k = \frac{c_{\mathrm{P},k} - c_{\mathrm{F},k}}{c_{\mathrm{F},k}}

where :math:`c_{P,k}` and :math:`c_{F,k}` are the specific product and fuel costs. Lowering
:math:`r_k` through efficiency improvements is recommended for cost optimization :cite:`Bejan1996`.


*************************************************
Getting started with exergoeconomic analysis
*************************************************

Prerequisites
=============

Before performing an exergoeconomic analysis, you need:

1. A completed exergy analysis with the split of the physical exergy into thermal and mechanical 
parts (:code:`split_physical_exergy=True`)
2. Chemical exergy enabled (recommended for systems with combustion)
3. Component investment cost rates and input stream specific costs

.. note::

    The exergoeconomic analysis is not applicable to models parsed from Aspen Plus, as
    Aspen does not provide the thermal and mechanical exergy splitting. In future version, 
    we plan to implement an alternative costing approach that does not require this splitting.

Workflow overview
=================

The exergoeconomic analysis in ExerPy follows four steps:

1. **Perform the exergy analysis** with physical exergy splitting enabled:

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

4. **View results**:

.. code-block:: python

    eco.exergoeconomic_results()
    eco.evaluate_results()

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

**Mandatory costs:**

- All components must have a :code:`_Z` cost (except :code:`CycleCloser` and :code:`PowerBus`, which are helper components)
- All material and power/heat streams entering the system boundary must have a :code:`_c` cost

**Examples:**

- :code:`"COMP_Z": 80.0` — compressor investment cost of 80 EUR/h
- :code:`"1_c": 0.0` — ambient air enters the system at zero cost
- :code:`"10_c": 25.0` — natural gas enters the system at 25 EUR/GJ


Interpreting results
====================

After running the analysis, use :code:`exergoeconomic_results()` to display the full results,
and :code:`evaluate_results()` to identify the components with the highest cost improvement potential.

.. code-block:: python

    # Display all results (4 DataFrames)
    df_comp, df_mat_props, df_mat_costs, df_non_mat = eco.exergoeconomic_results()

    # Identify top components for optimization
    eco.evaluate_results(sort_by="C_D+Z", top_n=5)

The component results table includes these key indicators:

- :math:`\dot{C}_F`, :math:`\dot{C}_P` — cost rates of fuel and product
- :math:`\dot{C}_D` — cost of exergy destruction
- :math:`\dot{Z}` — investment and O&M cost rate
- :math:`\dot{C}_D + \dot{Z}` — total cost rate (primary optimization target)
- :math:`f` — exergoeconomic factor:
    - **High** :math:`f` (close to 1): capital costs dominate — consider cheaper equipment or less material
    - **Low** :math:`f` (close to 0): inefficiency costs dominate — consider improving component efficiency
- :math:`r` — relative cost difference: indicates how much the specific cost increases from fuel to product

The :code:`evaluate_results()` method accepts the following :code:`sort_by` options:
:code:`"C_D+Z"` (default), :code:`"C_D"`, :code:`"Z"`, :code:`"r"`, :code:`"f"`.

To verify the integrity of the solution, use :code:`check_cost_balance()`:

.. code-block:: python

    balances = eco.check_cost_balance(tol=1e-3)
    for name, (residual, is_balanced) in balances.items():
        print(f"{name}: residual={residual:.6f}, balanced={is_balanced}")

Troubleshooting
===============

**Singular matrix error**

If the cost matrix is singular, the system of equations cannot be solved uniquely. To diagnose
the issue:

.. code-block:: python

    eco.print_dependency_report()

This reports zero rows/columns, colinear equations, and SVD null-space analysis. Common causes
include missing auxiliary equations for a component or redundant cost specifications.

As a workaround, you can use a least-squares solver:

.. code-block:: python

    eco.run(costs, allow_singular=True)

.. warning::

    The least-squares solution may not be physically consistent. Always verify the results
    with :code:`check_cost_balance()` when using :code:`allow_singular=True`.

**Missing cost error**

If you see :code:`ValueError: ... mandatory but not provided`, ensure that:

- Every component (except CycleCloser and PowerBus) has a :code:`"<name>_Z"` entry
- Every input stream crossing the system boundary has a :code:`"<name>_c"` entry

**split_physical_exergy requirement**

The exergoeconomic analysis requires :code:`split_physical_exergy=True` in the preceding exergy
analysis. If you see :code:`ValueError: split_physical_exergy must be True`, recreate the
:code:`ExergyAnalysis` instance with this parameter enabled.