.. _examples_label:

########
Examples
########

In the following three examples, we demonstrate how to use ExerPy to perform exergy analysis on different systems modelled in Ebsilon Professional, Aspen Plus and TESPy.

.. toctree::
    :maxdepth: 1
    :hidden:

    examples/ccpp.rst
    examples/heatpump.rst
    examples/cgam.rst

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

    **Air Source Heatpump**
    ^^^

    .. image:: /_static/images/flowsheets/heatpump.svg
      :align: center
      :alt: Heatpump flowsheet
      :class: only-light

    .. image:: /_static/images/flowsheets/heatpump_darkmode.svg
      :align: center
      :alt: Heatpump flowsheet
      :class: only-dark

    High-temperature air source heat pump that heats compressed water from 70 °C to 120 °C.

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

In the following example, we demonstrate how to use ExerPy to perform exergy analysis providing the results of system modelled with another software in a JSON format. 

.. toctree::
    :maxdepth: 1
    :hidden:

    examples/json.rst

.. card::
    :link: examples_json_label
    :link-type: ref

    **Custom JSON Example**

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

In the following example, we demonstrate how to extend the exergy analysis with exergoeconomic analysis to allocate costs to exergy streams.

.. toctree::
    :maxdepth: 1
    :hidden:

    examples/cgam_exergoeconomic.rst

.. card::
    :link: examples_cgam_exergoeconomic_label
    :link-type: ref

    **CGAM Exergoeconomic Example**
    ^^^

    Exergoeconomic analysis with manually defined component investment costs and
    input stream specific costs.

In the following example, we demonstrate how the purchase equipment costs of the components are turned into the cost rates the exergoeconomic analysis needs.

.. toctree::
    :maxdepth: 1
    :hidden:

    examples/heatpump_exergoeconomic.rst

.. card::
    :link: examples_heatpump_exergoeconomic_label
    :link-type: ref

    **From Equipment Costs to the Cost of the Product**
    ^^^

    The air source heat pump costed with the total revenue requirement method, from the
    purchase equipment cost of every component to the specific cost of the heat delivered.

In the following example, we demonstrate how the split of the physical exergy into a thermal and a mechanical share changes the result of an exergoeconomic analysis.

.. toctree::
    :maxdepth: 1
    :hidden:

    examples/split_physical_exergy.rst

.. card::
    :link: examples_split_physical_exergy_label
    :link-type: ref

    **Split Physical Exergy in Exergoeconomics**
    ^^^

    The CGAM process costed twice, with and without split physical exergy, with a
    comparison of the component and stream costs of the two.

In the following example, we demonstrate how to visualize the results of an exergy analysis with Sankey and waterfall diagrams.

.. toctree::
    :maxdepth: 1
    :hidden:

    examples/visualization.rst

.. card::
    :link: examples_visualization_label
    :link-type: ref

    **Visualization**
    ^^^

    Interactive Sankey diagrams of the exergy flows and waterfall diagrams of
    the exergy destruction per component for the three example systems.
