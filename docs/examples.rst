.. _examples_label:

########
Overview
########

The examples are sorted by the kind of analysis they show: the exergy analysis of plants modelled
in Ebsilon Professional, Aspen Plus, TESPy or given as JSON, the economic analysis that turns
equipment costs into cost rates, and the exergoeconomic analysis that combines the two. They
follow the workflow of ExerPy:

.. include:: /_workflow.rst

Exergy analysis
===============

.. card::
    :link: examples_ccpp_label
    :link-type: ref

    **Combined Cycle Power Plant**
    ^^^

    .. image:: /_static/images/flowsheets/combined_cycle_power_plant.svg
      :align: center
      :alt: Combined Cycle Power Plant flowsheet
      :class: only-light

    .. image:: /_static/images/flowsheets/combined_cycle_power_plant_darkmode.svg
      :align: center
      :alt: Combined Cycle Power Plant flowsheet
      :class: only-dark

    Combined cycle power plant that integrates gas and steam turbine cycles to
    produce 300 MW of net electrical power and 100 MW of thermal power.
    +++

.. card::
    :link: examples_heatpump_label
    :link-type: ref

    **Air Source Heat Pump**
    ^^^

    .. image:: /_static/images/flowsheets/heatpump.svg
      :align: center
      :alt: Heat pump flowsheet
      :class: only-light

    .. image:: /_static/images/flowsheets/heatpump_darkmode.svg
      :align: center
      :alt: Heat pump flowsheet
      :class: only-dark

    High-temperature air source heat pump that heats pressurized water from 70 °C to 120 °C.

    +++

.. card::
    :link: examples_cgam_label
    :link-type: ref

    **CGAM Problem**
    ^^^

    .. image:: /_static/images/flowsheets/cgam.svg
      :align: center
      :alt: CGAM flowsheet
      :class: only-light

    .. image:: /_static/images/flowsheets/cgam_darkmode.svg
      :align: center
      :alt: CGAM flowsheet
      :class: only-dark

    CGAM Process.

    +++
    Reference: :cite:`Valero1994`

.. card::
    :link: examples_json_label
    :link-type: ref

    **Custom JSON Example**

    The exergy analysis of a plant modelled in other software, given as a JSON file.

    .. code-block:: text

        {
            "components": {
                ...
            },
            "connections": {
                ...
            },
            "ambient_conditions": {
                ...
            },
            "settings": {
                ...
        }

.. card::
    :link: examples_visualization_label
    :link-type: ref

    **Visualization**
    ^^^

    Interactive Sankey diagrams of the exergy flows and waterfall diagrams of
    the exergy destruction per component for the three example systems.

Economic analysis
=================

.. card::
    :link: examples_heatpump_exergoeconomic_label
    :link-type: ref

    **From Equipment Costs to the Cost of the Product**
    ^^^

    The cost rates of the air source heat pump using the total revenue requirement method, from
    the purchased equipment cost of every component to the specific cost of the heat delivered.

.. card::
    :link: examples_purchase_costs_label
    :link-type: ref

    **Purchased Equipment Costs from Four Sources**
    ^^^

    The purchased equipment costs of the TESPy heat pump from known costs, scaled costs of reference
    components, user-defined cost equations and the correlations of OpenPyTEA :cite:`Tamarona2026`, and how to combine them.

Exergoeconomic analysis
=======================

.. card::
    :link: examples_cgam_exergoeconomic_label
    :link-type: ref

    **CGAM Exergoeconomic Example**
    ^^^

    Exergoeconomic analysis with manually defined component investment costs and
    specific costs of the input streams.

.. card::
    :link: examples_split_physical_exergy_label
    :link-type: ref

    **Split Physical Exergy in Exergoeconomics**
    ^^^

    The CGAM process analysed twice, with and without split physical exergy, with a
    comparison of the component and stream costs of the two.
