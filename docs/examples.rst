.. _examples_label:

########
Examples
########

*******************************************
Example 1: Combined Cycle Power Plant Model
*******************************************

This tutorial demonstrates how to perform an exergy analysis on an Ebsilon 
model using ExerPy. We will use a Combined Cycle Power Plant model (`ccpp.ebs`) 
and walk through each step to conduct the analysis and retrieve the results.
You can download the simulation model in Ebsilon here:
:download:`ccpp.ebs </../examples/ccpp/ccpp.ebs>`

1. **Import Necessary Modules:**

.. code-block:: python

    from exerpy import ExergyAnalysis

2. **Specify the Path to the Ebsilon Model File:**

.. code-block:: python

    model_path = 'ccpp.ebs'

3. **Initialize the Exergy Analysis:** 
Create an instance of the :code:`ExergyAnalysis` class using the :code:`from_ebsilon` method.
Since there is a combustion process in the power plant, it is necessary to specify 
the chemical exergy library to use. In this case, we will use the Ahrendts library.

.. code-block:: python

    ean = ExergyAnalysis.from_ebsilon(model_path, chemExLib='Ahrendts')

4. **Define Fuel, Product, and Loss Exergy Streams:** 
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

5. **Perform the Exergy Analysis:** 
Run the analysis by invoking the :code:`analyse` 
method on the :code:`ExergyAnalysis` instance, passing the defined fuel, product, 
and loss exergy streams.

.. code-block:: python

    ean.analyse(E_F=fuel, E_P=product, E_L=loss)

6. **Retrieve and Display Results:** 
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

**Full Example Code:**

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


