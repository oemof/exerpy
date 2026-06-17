.. _examples_json_exergoeconomic_label:

**************************************
CGAM Process (Exergoeconomic Analysis)
**************************************

This tutorial demonstrates how to perform an exergoeconomic analysis using ExerPy with
manually defined component and stream costs. 

.. note::

    This tutorial builds upon the :ref:`CGAM Process exergy analysis example <examples_cgam_label>` and uses 
    data imported from a previously saved JSON file. Make sure you understand how to set up exergy analysis 
    from JSON data before proceeding.


1. **Exergy Analysis (Prerequisite)**

Perform the exergy analysis. Note that the JSON example file already contains pre-computed
thermal and mechanical exergy values, so :code:`split_physical_exergy` defaults to :code:`True`:

.. literalinclude:: /../examples/exergoeconomic_analysis/json_example/example_json.py
    :language: python
    :start-after: [exergy_analysis_section]
    :end-before: [exergoeconomic_setup]

2. **Define Costs and Run the Exergoeconomic Analysis**

Create the :class:`~exerpy.analyses.ExergoeconomicAnalysis` instance and define all required costs
directly in a dictionary:

.. literalinclude:: /../examples/exergoeconomic_analysis/json_example/example_json.py
    :language: python
    :start-after: [exergoeconomic_setup]
    :end-before: [display_results]

The cost dictionary requires two types of entries:

- **Component investment costs** (:code:`<name>_Z`): the cost rate in EUR/h for each component.
  These represent the annualized capital investment plus operating and maintenance costs.
- **Input stream costs** (:code:`<name>_c`): the specific cost in EUR/GJ for each stream
  entering the system boundary. Ambient air is typically assigned a cost of 0.0.

3. **Display and Evaluate Results**

.. literalinclude:: /../examples/exergoeconomic_analysis/json_example/example_json.py
    :language: python
    :start-after: [display_results]
    :end-before: [end]

The :code:`evaluate_results()` method ranks components by their total cost rate
(:math:`\dot{C}_D + \dot{Z}`) to identify the most promising targets for optimization.
You can sort by different criteria using the :code:`sort_by` parameter:

.. code-block:: python

    # Sort by cost of exergy destruction only
    eco.evaluate_results(sort_by="C_D", top_n=3)

    # Sort by exergoeconomic factor
    eco.evaluate_results(sort_by="f", top_n=3)
