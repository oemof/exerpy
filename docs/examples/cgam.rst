.. _examples_cgam_label:

************
CGAM Process
************

This tutorial demonstrates how to perform an exergy analysis of a CGAM process using ExerPy.
The analysis is carried out with:

- Ebsilon
- Aspen Plus
- tespy

The flowsheet of the system is shown below.

.. figure:: /_static/images/flowsheets/cgam.svg
    :align: center
    :alt: CGAM flowsheet
    :figclass: only-light

    Figure: Flowsheet of the CGAM process model

.. figure:: /_static/images/flowsheets/cgam_darkmode.svg
    :align: center
    :alt: CGAM flowsheet
    :figclass: only-dark

    Figure: Flowsheet of the CGAM process model

.. note::

    The tespy based flowsheet has slight deviations from the show flowsheet,
    due to not using the identical component definitions. For example, Ebsilon provides a
    component incorporating drum, recirculation pump and evaporator in a single
    part, while these are individual components in tespy.

The import of the exerpy dependency is the same for all simulators:

1. **Import Necessary Modules**

.. code-block:: python

    from exerpy import ExergyAnalysis

.. tab-set::

   .. tab-item:: Ebsilon

        Download the Ebsilon simulation model here:
        :download:`cgam.ebs </../examples/cgam/cgam.ebs>`

        2. **Initialize the Exergy Analysis**

        Create an instance of the :code:`ExergyAnalysis` class using the :code:`from_ebsilon` method.
        Since there is a combustion process in the power plant, it is necessary to specify
        the chemical exergy library to use. In this case, we will use the Ahrendts library.
        You can decided weather to split the physical exergy into its mechanical and thermal shares
        by setting the :code:`split_physical_exergy` parameter to :code:`True` or :code:`False`.

        .. code-block:: python

            model_path = 'cgam.ebs'

            ean = ExergyAnalysis.from_ebsilon(model_path, chemExLib='Ahrendts', split_physical_exergy=False)

        3. **Define the exergy flows crossing the system boundaries**

        ExerPy requires you to specify the fuel (:code:`E_F`), product
        (:code:`E_P`), and loss (:code:`E_L`) exergy streams in your system.
        These are defined using dictionaries with :code:`"inputs"` and :code:`"outputs"`
        keys, containing lists of connection IDs from your Ebsilon model.

        .. code-block:: python

            fuel = {
                "inputs": ['1', '10'],
                "outputs": []
            }

            product = {
                "inputs": ['E1', '9'],
                "outputs": ['8']
            }

            loss = {
                "inputs": ['7'],
                "outputs": []
            }

        For this process, the exergetic fuel of the system (:code:`E_F`) is the
        methane flow (:code:`10`) and air flow (:code:`1`). The exergetic product of the system (:code:`E_P`) 
        consists of the net power output (:code:`E_1`) and the difference between the exergy of the vapour 
        outlet (:code:`9`) and of the water inlet (:code:`8`). The exhaust stream (:code:`7`) represents 
        the exergy loss of the system (:code:`E_L`).

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

                model_path = 'cgam.ebs'

                ean = ExergyAnalysis.from_ebsilon(model_path, chemExLib='Ahrendts', split_physical_exergy=False)

                fuel = {
                    "inputs": ['1', '10'],
                    "outputs": []
                }

                product = {
                    "inputs": ['E1', '9'],
                    "outputs": ['8']
                }

                loss = {
                    "inputs": ['7'],
                    "outputs": []
                }

                ean.analyse(E_F=fuel, E_P=product, E_L=loss)
                ean.exergy_results()

   .. tab-item:: tespy


   .. tab-item:: Aspen Plus

        Download the Aspen simulation model here:
        :download:`cgam.bkp </../examples/cgam/cgam.bkp>`

        2. **Initialize the Exergy Analysis**

        Create an instance of the :code:`ExergyAnalysis` class using the :code:`from_aspen` method.
        Since there is a combustion process in the power plant, it is necessary to specify
        the chemical exergy library to use. In this case, we will use the Ahrendts library.

        .. note::
            At the moment, it is not possible to split the physical exergy into its mechanical and thermal shares
            when using Aspen Plus. Therefore, the :code:`split_physical_exergy` parameter should be always set to :code:`False`
            when using the :code:`from_aspen` method.        

        .. code-block:: python

            model_path = 'cgam.bkp'

            ean = ExergyAnalysis.from_aspen(model_path, chemExLib='Ahrendts', split_physical_exergy=False)

        3. **Define the exergy flows crossing the system boundaries**

        ExerPy requires you to specify the fuel (:code:`E_F`), product
        (:code:`E_P`), and loss (:code:`E_L`) exergy streams in your system.
        These are defined using dictionaries with :code:`"inputs"` and :code:`"outputs"`
        keys, containing lists of connection IDs from your Aspen model.

        .. code-block:: python

            fuel = {
                "inputs": ['1', '10'],
                "outputs": []
            }

            product = {
                "inputs": ['E1', '9'],
                "outputs": ['8']
            }

            loss = {
                "inputs": ['7'],
                "outputs": []
            }

        For this process, the exergetic fuel of the system (:code:`E_F`) is the
        methane flow (:code:`10`) and air flow (:code:`1`). The exergetic product of the system (:code:`E_P`) 
        consists of the net power output (:code:`E_1`) and the difference between the exergy of the vapour 
        outlet (:code:`9`) and of the water inlet (:code:`8`). The exhaust stream (:code:`7`) represents 
        the exergy loss of the system (:code:`E_L`).

        .. note::

            The dictionary labels must exactly match the connection labels defined in the Aspen
            simulation model. It is strongly recommended to rename the stream labels
            in Aspen using consistent and meaningful labels.

            For example: use `"1"`, `"2"`, `"3"` for material connections and `"E1"`, `"E2"`, `"E3"` for
            electrical connections, `"H1"`, `"H2"`, `"H3"` for heat connections, etc.

        .. dropdown:: **Full Example Code:**

            .. code-block:: python

                from exerpy import ExergyAnalysis

                model_path = 'cgam.bkp'

                ean = ExergyAnalysis.from_aspen(model_path, chemExLib='Ahrendts', split_physical_exergy=False)

                fuel = {
                    "inputs": ['1', '10'],
                    "outputs": []
                }

                product = {
                    "inputs": ['E1', '9'],
                    "outputs": ['8']
                }

                loss = {
                    "inputs": ['7'],
                    "outputs": []
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
