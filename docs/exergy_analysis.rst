#####################
Exergy Analysis Intro
#####################

Exergy analysis is a powerful tool for evaluating and optimizing thermodynamic
systems. Unlike conventional energy analysis, which focuses on the quantity of
energy, exergy analysis considers both the quantity and quality of energy,
providing deeper insights into system inefficiencies. This approach helps
identify where and why irreversibilities occur, enabling engineers and
researchers to develop strategies for improving efficiency, reducing costs,
and supporting sustainable energy conversion.

The ExerPy library offers a flexible, Python-based solution for conducting
exergy analysis on energy-conversion systems. It supports integration with
simulation tools like Ebsilon Professional, Aspen Plus, and TESPy, allowing
users to extract detailed data about components and connections.

The features described in this section are based on a paper published for TESPy.
For more details, see :cite:`Witte2022`.


*******************************
Fundamentals of exergy analysis
*******************************

Energy is a concept of the first law of thermodynamics. It cannot be destroyed.
But regarding the design and analysis of thermal systems, the idea that
something can be destroyed is useful. According to the second law of
thermodynamics, the conversion of heat and internal energy into work is
limited. This constraint and the idea of destruction are applied to introduce a
new concept: "Exergy".

Exergy can be destroyed due to irreversibility and is able to describe the
quality of different energy forms. The difference in quality of different forms
of energy shall be illustrated by the following example. 1 kJ of electrical
energy is clearly more valuable than 1 kJ of energy in a glass of water at
ambient temperature :cite:`Bejan1996`.

In literature, exergy is defined as follows:

    *"An opportunity for doing useful work exists whenever two systems at
    different states are placed in communication, for in principle work can be
    developed as the two are allowed to come into equilibrium. When one of the
    two systems is a suitably idealized system called an environment and the
    other is some system of interest, exergy is the maximum theoretical useful
    work (shaft work or electrical work) obtainable as the systems interact to
    equilibrium, heat transfer occuring with the environment only."*
    :cite:`Bejan1996`


***********
Terminology
***********

The definitions and nomenclature of the exergy analysis in TESPy are based on
:cite:`Tsatsaronis2007`. The exergy destruction ratios are described in more
detail in :cite:`Bejan1996`. Since the current version of the exergy analysis
in TESPy only focuses on physical exergy and does not include reaction
processes yet, chemical exergy is not considered. Changes in kinetic and
potential exergy are neglected and therefore not considered as well.

.. list-table:: Terminology
    :widths: 15 20 15 50
    :header-rows: 1
    :class: tight-table

    * - variable
      - name
      - symbol
      - description
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
      - based on standard chemical exergy in ambient model, the `exerpy.data`
        module provides three different datasets for standard exergy based on
        various sources, i.e. `Ahrendts`
        :cite:`Ahrendts1980,Ahrendts1977,Ahrendts1974`, `Szargut1988`
        :cite:`Szargut1988` and `Szargut2007` :cite:`Szargut2007,Bakshi2011`.
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
      - :math:`y_\mathrm{D,k}`
      - rate of exergy destruction in a component compared to the exergy rate
        of the fuel provided to the overall system
    * - :code:`y_star`
      - exergy destruction ratio
      - :math:`y^*_\mathrm{D,k}`
      - rate of exergy destruction in a component compared to the total exergy
        destruction rate within the system

.. note::

    The generic exergy analysis balance equations have been implemented and tested
    only for the most common components. A list of components that have been considered
    can be found in the API documentation.