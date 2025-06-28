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