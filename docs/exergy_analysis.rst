.. _exergy_analysis_label:

###############
Exergy Analysis
###############

Exergy analysis is a powerful tool for evaluating and optimizing thermodynamic
systems. Unlike conventional energy analysis, which focuses on the quantity of
energy, exergy analysis considers both the quantity and the quality of energy,
providing deeper insights into system inefficiencies. This approach helps
identify where and why irreversibilities occur, enabling engineers and
researchers to develop strategies for improving efficiency, reducing costs,
and supporting sustainable energy conversion.

.. dropdown:: Where this step fits: step 1 of the workflow

    .. include:: /_workflow.rst

The ExerPy library offers a flexible, Python-based solution for conducting
exergy analysis on energy-conversion systems. It supports integration with
simulation tools like Ebsilon Professional, Aspen Plus, and TESPy, allowing
users to extract detailed data about components and connections.

The features described in this section are based on a paper on the exergy analysis in TESPy.
For more details, see :cite:`Witte2022`.


*******************************
Fundamentals of exergy analysis
*******************************

Energy is a concept of the first law of thermodynamics. It cannot be destroyed.
However, when it comes to the design and analysis of thermal systems, the idea that
something can be destroyed becomes useful. According to the second law of
thermodynamics, the conversion of heat and internal energy into work is
limited. This constraint and the idea of destruction are applied to introduce a
new concept: "Exergy".

Exergy can be destroyed due to irreversibilities. It also describes the
quality of different energy forms. The difference in energy quality can be illustrated by the following example: 1 kJ of electrical
energy is clearly more valuable than 1 kJ of energy in a glass of water at
ambient temperature :cite:`Bejan1996`.


In the literature, exergy is defined as follows:

    *"An opportunity for doing useful work exists whenever two systems at
    different states are placed in communication, for in principle work can be
    developed as the two are allowed to come into equilibrium. When one of the
    two systems is a suitably idealized system called an environment and the
    other is some system of interest, exergy is the maximum theoretical useful
    work (shaft work or electrical work) obtainable as the systems interact to
    equilibrium, heat transfer occurring with the environment only."*
    :cite:`Bejan1996`

Physical exergy
===============

In many energy conversion systems, chemical reactions are absent. In such cases, 
the consideration of chemical exergy is not necessary. Additionally, when the 
contributions of potential and kinetic exergy are negligible, the focus is 
exclusively on physical exergy. The specific physical exergy of stream :math:`i` 
is defined as :cite:`Bejan1996`:

.. math::

    e^\mathrm{PH}_i = h_i - h_0 - T_0 (s_i - s_0)

where :math:`h_i` and :math:`s_i` are the specific enthalpy and entropy at state 
:math:`i`, and :math:`h_0` and :math:`s_0` are the specific enthalpy and entropy 
at ambient conditions (:math:`T_0`, :math:`p_0`).

.. warning::

    For substances that are not fluid under ambient conditions, the physical 
    exergy calculation requires a modified approach. In such cases, the specific 
    physical exergy is calculated as:

    .. math::

        e^\mathrm{PH}_i = h_i - h_\mathrm{min} - T_0 (s_i - s_\mathrm{min})

    where the subscript "min" refers to the modified state at the given pressure 
    but at the minimum possible temperature at which the substance remains in 
    its fluid state. For example, for a molten salt consisting of 60% NaNO₃ and 
    40% KNO₃, the minimum temperature is 200°C.

    This formulation has been validated with Ebsilon Professional only.

Splitting of physical exergy
=============================

Since some thermal systems include states below the ambient temperature, the splitting 
of physical exergy into thermal and mechanical parts enables a more comprehensive 
analysis of the system's components :cite:`morosuk2019splitting`. These two parts represent 
the contributions of the temperature and pressure to the physical exergy. This 
separation is particularly valuable for defining more meaningful exergetic 
efficiencies for components operating below ambient temperature and for components
where distinguishing between thermal and mechanical exergy contributions provides 
more precise thermodynamic characterization. The separation is given by:

.. math::

    e^\mathrm{PH}_i = e^\mathrm{T}_i + e^\mathrm{M}_i

with the thermal exergy defined as:

.. math::

    e^\mathrm{T}_i = h_i - h_A - T_0 (s_i - s_A)

and the mechanical exergy defined as:

.. math::

    e^\mathrm{M}_i = h_A - h_0 - T_0 (s_A - s_0)

In these expressions, state :math:`A` is at ambient temperature :math:`T_0` and 
pressure :math:`p_i`.

Component-level exergy balance
===============================

The exergy analysis at the component level uses standardized balance equations, 
following the approach developed by :cite:`Witte2022`. The exergy balance 
equation of component :math:`k` can be formulated as:

.. math::

    0 = \dot{E}_{\mathrm{F},k} - \dot{E}_{\mathrm{P},k} - \dot{E}_{\mathrm{D},k}

Each component :math:`k` is evaluated by three metrics that quantify its 
performance and losses: the exergetic efficiency :math:`\varepsilon_k`, the 
exergy destruction ratio :math:`y_{\mathrm{D},k}` measuring the share of the total fuel
exergy destroyed by component :math:`k`, and the exergy destruction ratio 
:math:`y^*_{\mathrm{D},k}` measuring the share of the total exergy destruction attributable 
to component :math:`k`:

.. math::

    \varepsilon_k = \frac{\dot{E}_{\mathrm{P},k}}{\dot{E}_{\mathrm{F},k}}

.. math::

    y_{\mathrm{D},k} = \frac{\dot{E}_{\mathrm{D},k}}{\dot{E}_{\mathrm{F,tot}}}

.. math::

    y^*_{\mathrm{D},k} = \frac{\dot{E}_{\mathrm{D},k}}{\dot{E}_{\mathrm{D,tot}}}

.. _heat_boundary_label:

Heat from or to outside the model
=================================

A component that exchanges heat with something the model does not contain, such as a furnace, a
heat source or a heat consumer, needs a rule for the exergy of that heat: the model knows the stream
that takes in or gives off the heat, but not the temperature on the other side. Where that
temperature :math:`T` is given, ExerPy values the heat at it,

.. math::

    \dot{E}_\mathrm{Q} = |\dot{Q}| \left(1 - \frac{T_0}{T}\right)

- A **steam generator** takes the temperature of its heat source as ``T_hot``; its fuel is the exergy
  of the heat at that temperature. Without ``T_hot``, the fuel is approximated by the thermal exergy
  the water and steam gain, and the component warns.
- A **simple heat exchanger** may take ``T_hot``, the temperature of the source of the heat it takes
  in, which then gives its fuel, or ``T_cold``, the temperature of the consumer of the heat it gives
  off, which then gives its product. Without them, the heat is valued at the exergy change of the
  stream itself, so the loss of the heat transfer to or from the outside lies outside the component.
  The option applies to streams above the ambient temperature; a source has to be hotter than the
  stream, and a consumer colder.

The exergy of the heat connection is set to the same value, so the totals of the plant and the costs
of the exergoeconomic analysis follow it. The temperatures are given in K, in the entry of the
component in a JSON file, or on the component once the model is loaded and before ``analyse()``:

.. code-block:: python

    ean = ExergyAnalysis.from_tespy(nw, Tamb, pamb)     # or from_ebsilon, from_aspen, from_json
    ean.components["SG"].T_hot = 1173.15                 # the furnace of a steam generator
    ean.components["HC"].T_cold = 363.15                 # a heating network supplied by a heat exchanger
    ean.analyse(E_F=fuel, E_P=product, E_L=loss)

The choice moves exergy destruction across the boundary of the component. In the combined cycle of
the examples, the extraction steam supplies 100 MW of heat through a simple heat exchanger: valued
at the steam, the heat carries 39.7 MW of exergy and the exchanger destroys none; delivered to a
heating network at 90 °C, the heat carries 20.7 MW, and the exchanger destroys the other 19.1 MW.

System-level exergy balance
============================

At the system level, the overall exergy balance is expressed as:

.. math::

    0 = \dot{E}_{\mathrm{F,tot}} - \dot{E}_{\mathrm{P,tot}} - \dot{E}_{\mathrm{D,tot}} - \dot{E}_{\mathrm{L,tot}}

where the fuel, product, and loss streams of the overall system need to be 
defined according to the thermodynamic purpose of the system under consideration.

***********
Terminology
***********

The definitions and nomenclature used in the exergy analysis in ExerPy are based on
:cite:`Tsatsaronis2007`. The exergy destruction ratios are described in more
detail in :cite:`Bejan1996`. Changes in kinetic and
potential exergy are neglected and therefore not considered.

.. list-table:: Terminology
    :widths: 15 20 15 50
    :header-rows: 1
    :class: tight-table

    * - Variable
      - Name
      - Symbol
      - Description
    * - :code:`e_PH`, :code:`E_PH`
      - (specific) physical exergy
      - :math:`e^\mathrm{PH}`, :math:`E^\mathrm{PH}`
      - due to the deviation of the temperature and pressure of the system from
        those of the environment
    * - :code:`e_T`, :code:`E_T`
      - (specific) thermal exergy
      - :math:`e^\mathrm{T}`, :math:`E^\mathrm{T}`
      - associated with the system temperature
    * - :code:`e_M`, :code:`E_M`
      - (specific) mechanical exergy
      - :math:`e^\mathrm{M}`, :math:`E^\mathrm{M}`
      - associated with the system pressure
    * - :code:`e_CH`, :code:`E_CH`
      - (specific) chemical exergy
      - :math:`e^\mathrm{CH}`, :math:`E^\mathrm{CH}`
      - based on the standard chemical exergies of the reference environment; the `exerpy.data`
        module provides the dataset of Ahrendts
        :cite:`Ahrendts1980,Ahrendts1977,Ahrendts1974`.
    * - :code:`E_P`
      - product exergy
      - :math:`\dot{E}_\mathrm{P}`
      - represents the desired result (expressed in terms of exergy) generated
        by the system being considered
    * - :code:`E_F`
      - fuel exergy
      - :math:`\dot{E}_\mathrm{F}`
      - represents the resources (expressed in terms of exergy) expended to
        provide the product exergy
    * - :code:`E_D`
      - exergy destruction
      - :math:`\dot{E}_\mathrm{D}`
      - thermodynamic inefficiencies associated with the irreversibility
        (entropy generation) within the system boundaries
    * - :code:`E_L`
      - exergy loss
      - :math:`\dot{E}_\mathrm{L}`
      - thermodynamic inefficiencies associated with the transfer of exergy
        through material and energy streams to the surroundings
    * - :code:`epsilon`
      - exergetic efficiency
      - :math:`\varepsilon`
      - ratio between product exergy and fuel exergy
    * - :code:`y`
      - exergy destruction ratio
      - :math:`y_{\mathrm{D},k}`
      - rate of exergy destruction in a component compared to the exergy rate
        of the fuel provided to the overall system
    * - :code:`y_star`
      - exergy destruction ratio
      - :math:`y^*_{\mathrm{D},k}`
      - rate of exergy destruction in a component compared to the total exergy
        destruction rate within the system

.. note::

    The generic exergy analysis balance equations have been implemented and tested
    only for the most common components. A list of components that have been considered
    can be found in the API documentation.
