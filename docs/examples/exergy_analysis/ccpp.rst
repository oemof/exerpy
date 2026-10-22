.. _examples_ccpp_label:

**************************
Combined Cycle Power Plant
**************************

.. seealso::

    The method behind this example: :ref:`Exergy Analysis <exergy_analysis_label>`.

This tutorial demonstrates how to perform an exergy analysis of a combined
cycle power plant using ExerPy. The analysis is carried out with:

- Ebsilon
- Aspen Plus
- tespy

The flowsheet of the system is shown below.

.. figure:: /_static/images/flowsheets/combined_cycle_power_plant.svg
    :align: center
    :alt: Combined cycle power plant flowsheet
    :figclass: only-light

    Figure: Flowsheet of the CCPP model

.. figure:: /_static/images/flowsheets/combined_cycle_power_plant_darkmode.svg
    :align: center
    :alt: Combined cycle power plant flowsheet
    :figclass: only-dark

    Figure: Flowsheet of the CCPP model

.. note::

    The tespy-based flowsheet deviates slightly from the flowsheet shown,
    because the component definitions are not identical. For example, while
    Ebsilon provides turbines that can have multiple outlets, in tespy users
    have to add a splitter downstream of the turbine and then connect the
    splitter to the components behind it. Similarly, Ebsilon provides a
    single component that combines the drum, the recirculation pump and the
    evaporator, while these are individual components in tespy.

Importing exerpy is the same for all simulators:

1. **Import Necessary Modules**

.. code-block:: python

    from exerpy import ExergyAnalysis

.. tab-set::

   .. tab-item:: Ebsilon

        Download the Ebsilon simulation model here:
        :download:`ccpp.ebs </../examples/exergy_analysis/ccpp/ccpp.ebs>`

        2. **Initialize the Exergy Analysis**

        Create an instance of the :code:`ExergyAnalysis` class using the :code:`from_ebsilon` method.
        Since there is a combustion process in the power plant, it is necessary to specify
        the chemical exergy library to use. In this case, we will use the Ahrendts library.
        You can decide whether to split the physical exergy into its mechanical and thermal shares
        by setting the :code:`split_physical_exergy` parameter to :code:`True` or :code:`False`.

        .. code-block:: python

            model_path = 'ccpp.ebs'

            ean = ExergyAnalysis.from_ebsilon(model_path, chemExLib='Ahrendts', split_physical_exergy=False)

        3. **Define the exergy flows crossing the system boundaries**

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

        For this power plant, the exergetic fuel of the system (:code:`E_F`) consists of
        the methane flow (:code:`1`) and the air flow (:code:`3`), which are the inputs to the combustion process.
        The exergetic product of the system (:code:`E_P`) is the net power output (:code:`ETOT`)
        and the exergy flow related to the heat flow extracted from the steam cycle (:code:`H1`).
        The exhaust stream (:code:`8`) and the difference between the exergy values of the cooling water
        outlet (:code:`15`) and inlet (:code:`14`) represent the exergy losses of the system
        (:code:`E_L`).

        .. note::

            The dictionary labels must exactly match the connection labels defined in the Ebsilon
            simulation model. By default, Ebsilon assigns generic names to streams
            (e.g., `"water"`, `"water_1"`). It is strongly recommended to give the streams
            consistent and meaningful labels in Ebsilon.

            For example, use `"1"`, `"2"`, `"3"` for material connections, `"E1"`, `"E2"`, `"E3"` for
            electrical connections, and `"H1"`, `"H2"`, `"H3"` for heat connections.

        .. dropdown:: Full code of this example

            .. literalinclude:: /../examples/exergy_analysis/ccpp/ccpp_ebs.py
                :language: python

   .. tab-item:: tespy

        For the tespy model, the code to run the simulation is provided
        in the dropdown below. To learn how to set up tespy models and what
        to be aware of when working with tespy, please refer to the
        `online documentation of tespy <https://tespy.readthedocs.io>`__.

        .. dropdown:: Code of the tespy model

            .. literalinclude:: /../examples/exergy_analysis/ccpp/ccpp_tespy.py
                :language: python
                :end-before: [tespy_model_section_end]

        2. **Initialize the Exergy Analysis**

        After setting up the model, we create the :code:`ExergyAnalysis`
        instance using the :code:`from_tespy` method. It takes the
        **converged** :code:`tespy.Network` object along with the ambient state and
        (optionally) the chemical exergy library as inputs.

        .. tip::

            TESPy provides the thermal and the mechanical shares of the physical exergy, so
            :code:`split_physical_exergy` can be set to :code:`True`. This example sets it to
            :code:`False` so that its results can be compared with those of Aspen Plus, which does not
            provide the split.

        .. literalinclude:: /../examples/exergy_analysis/ccpp/ccpp_tespy.py
            :language: python
            :start-after: [tespy_model_section_end]
            :end-before: [exergy_analysis_setup]

        3. **Define the exergy flows crossing the system boundaries**

        For this power plant, the exergetic fuel of the system (:code:`E_F`) consists
        of the methane flow (:code:`1`) and the air flow (:code:`3`), which are the
        inputs to the combustion process. The exhaust stream (:code:`8`) and
        the difference between the exergy values of the cooling water outlet
        (:code:`15`) and inlet (:code:`14`) represent the exergy losses
        of the system (:code:`E_L`). The product exergy (:code:`E_P`) is the
        sum of the electrical energy :code:`ETOT` and the exergy of the heat
        :code:`H1`.

        .. literalinclude:: /../examples/exergy_analysis/ccpp/ccpp_tespy.py
            :language: python
            :start-after: [exergy_analysis_setup]
            :end-before: [exergy_analysis_flows]

        .. dropdown:: Full code of this example

            .. literalinclude:: /../examples/exergy_analysis/ccpp/ccpp_tespy.py
                :language: python

   .. tab-item:: Aspen Plus

        Download the Aspen simulation model here:
        :download:`ccpp.bkp </../examples/exergy_analysis/ccpp/ccpp.bkp>`

        2. **Initialize the Exergy Analysis**

        Create an instance of the :code:`ExergyAnalysis` class using the :code:`from_aspen` method.
        Since there is a combustion process in the power plant, it is necessary to specify
        the chemical exergy library to use. In this case, we will use the Ahrendts library.

        .. note::

            Aspen Plus does not provide the thermal and the mechanical shares of the physical exergy, so
            :code:`split_physical_exergy` has to be set to :code:`False` with :code:`from_aspen`. The
            exergoeconomic analysis runs on such a model as well: it then assigns one cost to the
            physical exergy of each stream (see :ref:`Split Physical Exergy in Exergoeconomics
            <examples_split_physical_exergy_label>`).

        .. code-block:: python

            model_path = 'ccpp.bkp'

            ean = ExergyAnalysis.from_aspen(model_path, chemExLib='Ahrendts', split_physical_exergy=False)

        3. **Define the exergy flows crossing the system boundaries**

        ExerPy requires you to specify the fuel (:code:`E_F`), product
        (:code:`E_P`), and loss (:code:`E_L`) exergy streams in your system.
        These are defined using dictionaries with :code:`"inputs"` and :code:`"outputs"`
        keys, containing lists of connection IDs from your Aspen model.

        .. code-block:: python

            fuel = {
                "inputs": ['1', '3'],
                "outputs": []
            }

            product = {
                "inputs": ['ETOT', 'HC_HEAT'],
                "outputs": []
            }

            loss = {
                "inputs": ['8', '15'],
                "outputs": ['14']
            }

        For this power plant, the exergetic fuel of the system (:code:`E_F`) consists of
        the methane flow (:code:`1`) and the air flow (:code:`3`), which are the inputs to the combustion process.
        The exergetic product of the system (:code:`E_P`) is the net power output (:code:`ETOT`)
        and the exergy flow related to the heat flow extracted from the steam cycle (:code:`HC_HEAT`).
        The exhaust stream (:code:`8`) and the difference between the exergy values of the cooling water
        outlet (:code:`15`) and inlet (:code:`14`) represent the exergy losses of the system
        (:code:`E_L`).

        .. note::

            The dictionary labels must exactly match the connection labels defined in the Aspen
            simulation model. It is strongly recommended to give the streams
            consistent and meaningful labels in Aspen.

            For example, use `"1"`, `"2"`, `"3"` for material connections, `"E1"`, `"E2"`, `"E3"` for
            electrical connections, and `"H1"`, `"H2"`, `"H3"` for heat connections.

        .. dropdown:: Full code of this example

            .. literalinclude:: /../examples/exergy_analysis/ccpp/ccpp_aspen.py
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
