.. _examples_heatpump_label:

*********
Heat Pump
*********

.. seealso::

    The method behind this example: :ref:`Exergy Analysis <exergy_analysis_label>`.

This tutorial demonstrates how to perform an exergy analysis of a heat pump using ExerPy.
The analysis is carried out with:

- Ebsilon
- Aspen Plus
- tespy

The flowsheet of the system is shown below.

.. figure:: /_static/images/flowsheets/heatpump.svg
    :align: center
    :alt: Heat pump flowsheet
    :figclass: only-light

    Figure: Flowsheet of the heat pump model

.. figure:: /_static/images/flowsheets/heatpump_darkmode.svg
    :align: center
    :alt: Heat pump flowsheet
    :figclass: only-dark

    Figure: Flowsheet of the heat pump model

Importing exerpy is the same for all simulators:

1. **Import Necessary Modules**

.. code-block:: python

    from exerpy import ExergyAnalysis

.. tab-set::

    .. tab-item:: Ebsilon

        Download the Ebsilon simulation model here:
        :download:`hp.ebs </../examples/exergy_analysis/heatpump/hp.ebs>`

        2. **Initialize the Exergy Analysis**

        Create an instance of the :code:`ExergyAnalysis` class using the :code:`from_ebsilon` method.
        Since this system operates at temperatures below the ambient temperature, it is strongly
        recommended to split the physical exergy into its mechanical and thermal parts
        by setting the :code:`split_physical_exergy` parameter to :code:`True`.

        .. code-block:: python

            model_path = 'hp.ebs'

            ean = ExergyAnalysis.from_ebsilon(model_path, split_physical_exergy=True)

        3. **Define the exergy flows crossing the system boundaries**

        ExerPy requires you to specify the fuel (:code:`E_F`), product
        (:code:`E_P`), and loss (:code:`E_L`) exergy streams in your system.
        These are defined using dictionaries with :code:`"inputs"` and :code:`"outputs"`
        keys, containing lists of connection IDs from your Ebsilon model.

        .. code-block:: python

            fuel = {
                "inputs": ['E1', 'E2', 'E3'],
                "outputs": []
            }

            product = {
                "inputs": ['23'],
                "outputs": ['21']
            }

            loss = {
                "inputs": ['13'],
                "outputs": ['11']
            }

        For this process, the exergetic fuel of the system (:code:`E_F`) is the sum of the inlet power flows
        (:code:`E1`, :code:`E2`, :code:`E3`). The exergetic product of the system (:code:`E_P`) is the
        difference between the exergy of the hot water outlet (:code:`23`) and the exergy of the cold water
        inlet (:code:`21`). Air is the heat source of the system. However, it enters the system at the ambient state
        and is released at a lower temperature. Therefore, the difference between the exergy of the air outlet (:code:`13`)
        and the exergy of the air inlet (:code:`11`) represents the exergy loss of the system (:code:`E_L`).

        .. note::

            The dictionary labels must exactly match the connection labels defined in the Ebsilon
            simulation model. By default, Ebsilon assigns generic names to streams
            (e.g., `"water"`, `"water_1"`). It is strongly recommended to give the streams
            consistent and meaningful labels in Ebsilon.

            For example, use `"1"`, `"2"`, `"3"` for material connections, `"E1"`, `"E2"`, `"E3"` for
            electrical connections, and `"H1"`, `"H2"`, `"H3"` for heat connections.

        .. dropdown:: Full code of this example

            .. literalinclude:: /../examples/exergy_analysis/heatpump/hp_ebs.py
                :language: python

    .. tab-item:: tespy

        For the tespy model, the code to run the simulation is provided
        in the dropdown below. To learn how to set up tespy models and what
        to be aware of when working with tespy, please refer to the
        `online documentation of tespy <https://tespy.readthedocs.io>`__.

        .. dropdown:: Code of the tespy model

            .. literalinclude:: /../examples/exergy_analysis/heatpump/hp_tespy.py
                :language: python
                :end-before: [tespy_model_section_end]

        2. **Initialize the Exergy Analysis**

        After setting up the model, we create the :code:`ExergyAnalysis`
        instance using the :code:`from_tespy` method. It takes the
        **converged** :code:`tespy.Network` object along with the ambient state and
        (optionally) the chemical exergy library as inputs.

        .. tip::

            TESPy provides the thermal and the mechanical shares of the physical exergy, so
            :code:`split_physical_exergy` can be set to :code:`True`, as in this example.

        .. literalinclude:: /../examples/exergy_analysis/heatpump/hp_tespy.py
            :language: python
            :start-after: [tespy_model_section_end]
            :end-before: [exergy_analysis_setup]

        3. **Define the exergy flows crossing the system boundaries**

        For this plant, the exergetic fuel of the system (:code:`E_F`) is the
        total electrical power input to the three motors. The cold air
        leaving the evaporator on the heat source side is considered an exergy
        loss of the system (:code:`E_L`), and the change in exergy from the
        liquid water to the steam is considered the exergy product (:code:`E_P`).

        .. literalinclude:: /../examples/exergy_analysis/heatpump/hp_tespy.py
            :language: python
            :start-after: [exergy_analysis_setup]
            :end-before: [exergy_analysis_flows]

        .. dropdown:: Full code of this example

            .. literalinclude:: /../examples/exergy_analysis/heatpump/hp_tespy.py
                :language: python

    .. tab-item:: Aspen Plus

        Download the Aspen simulation model here:
        :download:`hp.bkp </../examples/exergy_analysis/heatpump/hp.bkp>`

        2. **Initialize the Exergy Analysis**

        Create an instance of the :code:`ExergyAnalysis` class using the :code:`from_aspen` method.
        Since this system operates at temperatures below the ambient temperature, it is strongly
        recommended to split the physical exergy into its mechanical and thermal parts
        by setting the :code:`split_physical_exergy` parameter to :code:`True`.

        .. note::

            Aspen Plus reports the physical exergy of a stream, but not its thermal and mechanical
            shares. For the split, ExerPy adds a property analysis for each stream to the model in
            memory and runs the simulation once. The analysis evaluates the stream at the ambient
            temperature and its own pressure, with the property method of the stream. The model file
            stays unchanged.

        .. code-block:: python

            model_path = 'hp.bkp'

            ean = ExergyAnalysis.from_aspen(model_path, split_physical_exergy=True)

        3. **Define the exergy flows crossing the system boundaries**

        ExerPy requires you to specify the fuel (:code:`E_F`), product
        (:code:`E_P`), and loss (:code:`E_L`) exergy streams in your system.
        These are defined using dictionaries with :code:`"inputs"` and :code:`"outputs"`
        keys, containing lists of connection IDs from your Aspen model.

        .. code-block:: python

            fuel = {
                "inputs": ['E1', 'E2', 'E3'],
                "outputs": []
            }

            product = {
                "inputs": ['23'],
                "outputs": ['21']
            }

            loss = {
                "inputs": ['13'],
                "outputs": ['11']
            }

        For this process, the exergetic fuel of the system (:code:`E_F`) is the sum of the inlet power flows
        (:code:`E1`, :code:`E2`, :code:`E3`). The exergetic product of the system (:code:`E_P`) is the
        difference between the exergy of the hot water outlet (:code:`23`) and the exergy of the cold water
        inlet (:code:`21`). Air is the heat source of the system. However, it enters the system at the ambient state
        and is released at a lower temperature. Therefore, the difference between the exergy of the air outlet (:code:`13`)
        and the exergy of the air inlet (:code:`11`) represents the exergy loss of the system (:code:`E_L`).

        .. note::

            The dictionary labels must exactly match the connection labels defined in the Aspen
            simulation model. It is strongly recommended to give the streams
            consistent and meaningful labels in Aspen.

            For example, use `"1"`, `"2"`, `"3"` for material connections, `"E1"`, `"E2"`, `"E3"` for
            electrical connections, and `"H1"`, `"H2"`, `"H3"` for heat connections.

        .. dropdown:: Full code of this example

            .. literalinclude:: /../examples/exergy_analysis/heatpump/hp_aspen.py
                :language: python


From here on, running the exergy analysis and working with the results is
independent of the simulator.

4. **Perform the Exergy Analysis**

Run the analysis by invoking the :code:`analyse`
method on the :code:`ExergyAnalysis` instance, passing the defined fuel, product,
and loss exergy streams.

.. code-block:: python

    ean.analyse(E_F=fuel, E_P=product, E_L=loss)

5. **Retrieve and Display Results**

After the analysis is complete,
retrieve the results using the :code:`exergy_results` method.

.. code-block:: python

    # Retrieve and display the results
    df_components, df_material_connections, df_non_material_connections = ean.exergy_results()

    # Print the components exergy results
    print(df_components)

    # Optionally, save the results to CSV files
    df_components.to_csv('components_exergy_results.csv')
    df_material_connections.to_csv('material_connections_exergy_results.csv')
    df_non_material_connections.to_csv('non_material_connections_exergy_results.csv')
