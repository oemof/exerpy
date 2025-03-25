.. _examples_heatpump_label:

*********
Heat Pump
*********

This tutorial demonstrates how to perform an exergy analysis of a heat pump using ExerPy.
The analysis is carried out with:

- Ebsilon
- Aspen Plus
- tespy

The flowsheet of the system is shown below.

.. figure:: /_static/images/flowsheets/heatpump.svg
    :align: center
    :alt: Heatpump flowsheet
    :figclass: only-light

    Figure: Flowsheet of the heat pump model

.. figure:: /_static/images/flowsheets/heatpump_darkmode.svg
    :align: center
    :alt: Heatpump flowsheet
    :figclass: only-dark

    Figure: Flowsheet of the heat pump model

The import of the exerpy dependency is the same for all simulators:

1. **Import Necessary Modules**

.. code-block:: python

    from exerpy import ExergyAnalysis

.. tab-set::

   .. tab-item:: Ebsilon

        Download the Ebsilon simulation model here:
        :download:`hp.ebs </../examples/heatpump/hp.ebs>`

        2. **Initialize the Exergy Analysis**

        Create an instance of the :code:`ExergyAnalysis` class using the :code:`from_ebsilon` method.
        Since this system operates at temperature under the ambient temperature, it is strongly
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
        (:code:`E1`, :code:`E2`, :code:`E3`). The exergetic product of the system (:code:`E_P`) consists of the
        difference between the exergy of the hot water outlet (:code:`23`) and the exergy of the cold water
        inlet (:code:`21`). Air is the heat source of the system. However, it enters the system at the ambient state
        and is released at a lower temperature. Therefore, the difference between the exergy of the air outlet (:code:`13`)
        and the exergy of the air inlet (:code:`11`) represents the exergy loss of the system (:code:`E_L`).

        .. note::

            The dictionary labels must exactly match the connection labels defined in the Ebsilon
            simulation model. By default, Ebsilon assigns generic names to streams
            (e.g., `"water"`, `"water_1"`). It is strongly recommended to rename the stream labels
            in Ebsilon using consistent and meaningful labels.

            For example: use `"1"`, `"2"`, `"3"` for material connections and `"E1"`, `"E2"`, `"E3"` for
            electrical connections, `"H1"`, `"H2"`, `"H3"` for heat connections, etc.

        .. dropdown:: **Full Example Code:**

            .. code-block:: python

                from exerpy import ExergyAnalysis

                model_path = 'hp.ebs'

                ean = ExergyAnalysis.from_ebsilon(model_path, chemExLib='Ahrendts', split_physical_exergy=False)

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

                ean.analyse(E_F=fuel, E_P=product, E_L=loss)
                ean.exergy_results()

   .. tab-item:: tespy


   .. tab-item:: Aspen Plus

        Download the Aspen simulation model here:
        :download:`hp.bkp </../examples/heatpump/hp.bkp>`

        2. **Initialize the Exergy Analysis**

        Create an instance of the :code:`ExergyAnalysis` class using the :code:`from_aspen` method.
        This system operates at temperature under the ambient temperature. Therefore it should be 
        good practise to split the physical exergy into its mechanical and thermal parts
        by setting the :code:`split_physical_exergy` parameter to :code:`True`. However, at the moment,
        it is not possible to split the physical exergy into its mechanical and thermal shares
        when using Aspen Plus. Therefore, the :code:`split_physical_exergy` parameter is not available
        when using the :code:`from_aspen` method.

        .. note::
            At the moment, it is not possible to split the physical exergy into its mechanical and thermal shares
            when using Aspen Plus. Therefore, the :code:`split_physical_exergy` parameter should be always set to :code:`False`
            when using the :code:`from_aspen` method.        

        .. code-block:: python

            model_path = 'hp.bkp'

            ean = ExergyAnalysis.from_aspen(model_path, chemExLib='Ahrendts', split_physical_exergy=False)

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
        (:code:`E1`, :code:`E2`, :code:`E3`). The exergetic product of the system (:code:`E_P`) consists of the
        difference between the exergy of the hot water outlet (:code:`23`) and the exergy of the cold water
        inlet (:code:`21`). Air is the heat source of the system. However, it enters the system at the ambient state
        and is released at a lower temperature. Therefore, the difference between the exergy of the air outlet (:code:`13`)
        and the exergy of the air inlet (:code:`11`) represents the exergy loss of the system (:code:`E_L`).

        .. note::

            The dictionary labels must exactly match the connection labels defined in the Aspen
            simulation model. It is strongly recommended to rename the stream labels
            in Aspen using consistent and meaningful labels.

            For example: use `"1"`, `"2"`, `"3"` for material connections and `"E1"`, `"E2"`, `"E3"` for
            electrical connections, `"H1"`, `"H2"`, `"H3"` for heat connections, etc.

        .. dropdown:: **Full Example Code:**

            .. code-block:: python

                from exerpy import ExergyAnalysis

                model_path = 'heatpump.bkp'

                ean = ExergyAnalysis.from_aspen(model_path, chemExLib='Ahrendts', split_physical_exergy=False)

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

                ean.analyse(E_F=fuel, E_P=product, E_L=loss)
                ean.exergy_results()


Running the exergy analysis and working with the results is now
independant for all simulators.

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
