
.. _examples_ccpp_label:

********************************
Combined Cycle Power Plant Model
********************************

This tutorial demonstrates how to perform an exergy analysis of a combined
cycle power plant using ExerPy. The analysis is carried out with

- Ebsilon and
- tespy

The flowsheet of the system is shown below.

.. figure:: /_static/images/flowsheets/combined_cycle_power_plant.svg
    :align: center
    :alt: Combined cycle power plant flowsheet
    :figclass: only-light

    Figure: Flowsheet of the model

.. figure:: /_static/images/flowsheets/combined_cycle_power_plant_darkmode.svg
    :align: center
    :alt: Combined cycle power plant flowsheet
    :figclass: only-dark

    Figure: Flowsheet of the model

.. note::

    The tespy based flowsheet has slight deviations from the show flowsheet,
    due to not using the identical component definitions. For example, while
    Ebsilon provides turbines, which can have multiple outlets, in tespy users
    have to add a splitter downstream of the turbine and then connect the
    splitter to the components behind that. Similarly, Ebsilon provides a
    component incorporating drum, recirculation pump and evaporator in a single
    part, while these are individual components in tespy.

The import of the exerpy dependency is the same for all simulators:

1. **Import Necessary Modules:**

.. code-block:: python

    from exerpy import ExergyAnalysis

.. tab-set::

   .. tab-item:: Ebsilon

        Download the Ebsilon simulation model here:
        :download:`ccpp.ebs </../examples/ccpp/ccpp.ebs>`

        2. **Initialize the Exergy Analysis:**
        Create an instance of the :code:`ExergyAnalysis` class using the :code:`from_ebsilon` method.
        Since there is a combustion process in the power plant, it is necessary to specify
        the chemical exergy library to use. In this case, we will use the Ahrendts library.

        .. code-block:: python

            model_path = 'ccpp.ebs'

            ean = ExergyAnalysis.from_ebsilon(model_path, chemExLib='Ahrendts')

        3. **Define Fuel, Product, and Loss Exergy Streams:**
        ExerPy requires you to specify the fuel (:code:`E_F`), product
        (:code:`E_P`), and loss (:code:`E_L`) exergy streams in your system.
        These are defined using dictionaries with :code:`"inputs"` and :code:`"outputs"`
        keys, containing lists of connection IDs from your Ebsilon model.

        .. code-block:: python

            fuel = {
                "inputs": ['1', '3'],
                "outputs": []
            }

            product = {
                "inputs": ['ETOT', 'H1'],
                "outputs": []
            }

            loss = {
                "inputs": ['8', '15'],
                "outputs": ['14']
            }

        For this power plant, the exergetic fuel of the system (:code:`E_F`) is the
        methane flow (:code:`1`) and air flow (:code:`3`), which are the inputs to the combustion process.
        The exergetic product of the system (:code:`E_P`) is the net power output (:code:`E_TOT`)
        and the exergy flow related to the heat flow extracted from the steam cycle (:code:`H1`).
        The exhaust stream (:code:`8`) and the difference between the exergy values of the outlet
        (:code:`15`) and the inlet cooling water stream (:code:`14`) represent the exergy losses of the system.
        (:code:`E_L`).

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

                model_path = 'ccpp.ebs'

                ean = ExergyAnalysis.from_ebsilon(model_path, chemExLib='Ahrendts')

                fuel = {
                    "inputs": ['1', '3'],
                    "outputs": []
                }

                product = {
                    "inputs": ['ETOT', 'H1'],
                    "outputs": []
                }

                loss = {
                    "inputs": ['8', '15'],
                    "outputs": ['14']
                }

                ean.analyse(E_F=fuel, E_P=product, E_L=loss)
                ean.exergy_results()

   .. tab-item:: tespy

        For the tespy model we have prepared the code to run the simulation
        in the dropdown below. To learn how to set up tespy models and what
        things to be aware of when working with tespy, we kindly refer to the
        `online documentation of tespy <https://tespy.readthedocs.io>`__.

        .. dropdown:: Code of the tespy model

            .. literalinclude:: /../examples/ccpp/ccpp_tespy.py
                :language: python
                :end-before: [tespy_model_section_end]

        After setting up the model, we set up the :code:`ExergyAnalysis`
        instances using the :code:`from_tespy` method. It takes the
        **converged** :code:`tespy.Network` object along with ambient state and
        (optionally) the chemical exergy library as inputs.

        .. tip::

            TESPy can handle the splitting of physical exergy into its mechanical
            and thermal shares, therefore :code:`split_phyiscal_exergy` can
            always be set to :code:`True` when using tespy. In this instance it is
            set to :code:`False` because ASPEN cannot handle this, and we wanted to
            cross validate the results of the examples for all three simulators.

        2. **Set up the exergy analysis instance**

        .. literalinclude:: /../examples/ccpp/ccpp_tespy.py
            :language: python
            :start-after: [tespy_model_section_end]
            :end-before: [exergy_analysis_setup]

        3. **Define the exergy flows crossing the system boundaries**

        .. literalinclude:: /../examples/ccpp/ccpp_tespy.py
            :language: python
            :start-after: [exergy_analysis_setup]
            :end-before: [exergy_analysis_flows]

Running the actial exergy analysis and working with the results is now
independant for all simulators.

4. **Perform the Exergy Analysis:**

Run the analysis by invoking the :code:`analyse`
method on the :code:`ExergyAnalysis` instance, passing the defined fuel, product,
and loss exergy streams.

.. code-block:: python

    ean.analyse(E_F=fuel, E_P=product, E_L=loss)

5. **Retrieve and Display Results:**
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
