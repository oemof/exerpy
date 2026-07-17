.. _examples_visualization_label:

*************
Visualization
*************

ExerPy can visualize the results of a completed exergy analysis as an
interactive Sankey diagram of all exergy flows and as a waterfall diagram of
the exergy destruction per component. The plotting libraries are an optional
dependency, install them with:

.. code-block:: bash

    pip install exerpy[viz]

The examples below build the diagrams from the exported analysis results of
the three example systems, so no simulator is required to run them, e.g.:

.. code-block:: bash

    python examples/visualization/ccpp_diagrams.py

Sankey diagram
==============

:code:`plot_sankey` renders the exergy flows between all components of the
system together with four terminal nodes for the exergetic fuel (E_F), product
(E_P), destruction (E_D) and loss (E_L). If a fuel, product or loss definition
contains both inputs and outputs, an intermediate "net" node displays the
gross flows next to the net value. The most important options are:

- :code:`mode` – level of detail of the material links: :code:`1` shows the
  total exergy flow E per connection, :code:`2` splits each material link into
  physical and chemical exergy (requires chemical exergy), and :code:`3`
  splits into thermal, mechanical and chemical exergy (requires
  :code:`split_physical_exergy=True`).
- :code:`collapse_passthroughs` – hides pure pass-through components
  (by default the :code:`CycleCloser`).
- :code:`groups` – aggregates several components into a single node and hides
  the connections between them, e.g. to represent a subsystem.
- :code:`node_colors` – overrides the color of individual component nodes.
  Link colors are assigned automatically based on the type of flow (power,
  heat, or material by fluid).
- :code:`output_path` – exports the interactive diagram to an HTML file.

Waterfall diagram
=================

:code:`plot_exergy_waterfall` (Matplotlib) and
:code:`plot_exergy_waterfall_plotly` (interactive Plotly variant) display the
exergy destruction per component as percentages of the total fuel exergy, from
the exergetic fuel (100 %) down to the exergetic product. The bar colors can
be customized with the :code:`colors` dict using the keys :code:`"fuel"`,
:code:`"destruction"`, :code:`"loss"` and :code:`"product"`.

Examples
========

.. tab-set::

   .. tab-item:: CCPP

        1. **Load the results and run the analysis**

        .. literalinclude:: /../examples/visualization/ccpp_diagrams.py
            :language: python
            :start-after: [analysis_section]
            :end-before: [sankey_section]

        2. **Create the Sankey diagrams**

        .. literalinclude:: /../examples/visualization/ccpp_diagrams.py
            :language: python
            :start-after: [sankey_section]
            :end-before: [waterfall_section]

        3. **Create the waterfall diagrams**

        .. literalinclude:: /../examples/visualization/ccpp_diagrams.py
            :language: python
            :start-after: [waterfall_section]
            :end-before: [show_section]

   .. tab-item:: Heat Pump

        1. **Load the results and run the analysis**

        .. literalinclude:: /../examples/visualization/hp_diagrams.py
            :language: python
            :start-after: [analysis_section]
            :end-before: [sankey_section]

        2. **Create the Sankey diagrams**

        .. literalinclude:: /../examples/visualization/hp_diagrams.py
            :language: python
            :start-after: [sankey_section]
            :end-before: [waterfall_section]

        3. **Create the waterfall diagrams**

        .. literalinclude:: /../examples/visualization/hp_diagrams.py
            :language: python
            :start-after: [waterfall_section]
            :end-before: [show_section]

   .. tab-item:: CGAM

        1. **Load the results and run the analysis**

        .. literalinclude:: /../examples/visualization/cgam_diagrams.py
            :language: python
            :start-after: [analysis_section]
            :end-before: [sankey_section]

        2. **Create the Sankey diagrams**

        .. literalinclude:: /../examples/visualization/cgam_diagrams.py
            :language: python
            :start-after: [sankey_section]
            :end-before: [waterfall_section]

        3. **Create the waterfall diagrams**

        .. literalinclude:: /../examples/visualization/cgam_diagrams.py
            :language: python
            :start-after: [waterfall_section]
            :end-before: [show_section]
