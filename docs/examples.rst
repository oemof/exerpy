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

    .. code-block:: json

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

