#################
API Documentation
#################

The ExerPy package offers a flexible, Python-based solution for conducting exergy
analysis of energy-conversion systems. The current release supports integration with
three simulation tools: Ebsilon Professional, Aspen Plus, and TESPy, and allows users to extract detailed simulation
data of components and connections. The framework follows a structured workflow
that includes data parsing, physical and chemical exergy calculations, and the
generation of comprehensive exergy analysis results.

This section provides detailed information about the Application Programming
Interface (API) of ExerPy. The API is divided into two main modules:

1. **Parsing and Data Preparation**
2. **Exergy Analysis**


*************************************
1. Model Parsing and Data Preparation
*************************************

ExerPy supports parsing models from different simulation tools to extract and prepare data for exergy calculations:

.. list-table:: Supported Simulation Tools
    :header-rows: 1

    * - Tool
      - Description
      - License type
      - Supported version
      - Operating system
    * - `Ebsilon Professional <https://www.ebsilon.com/en/>`__
      - A comprehensive tool for simulating and analyzing energy systems, particularly in the field of power plant engineering.
      - Commercial
      - 17.0
      - Windows
    * - `Aspen Plus <https://www.aspentech.com/en/products/engineering/aspen-plus>`__
      - A powerful process simulation software used for designing and optimizing chemical processes.
      - Commercial
      - 14.5
      - Windows
    * - `TESPy <https://tespy.readthedocs.io/>`__
      - A versatile Python package for simulating thermal energy systems.
      - Open Source
      - 0.7.7 or later
      - Windows, macOS, Linux

.. note::

    Note that Ebsilon Professional and Aspen Plus require a valid commercial
    license for use. Additionally, while these tools are designed only for
    Windows, they can also be operated on macOS or Linux through the use of a
    virtual machine.

======
Inputs
======

This module requires the user to provide the following inputs:

- **Simulation model**: The model file from the supported simulation tools (e.g., Ebsilon Professional :code:`.ebs`, Aspen Plus :code:`.bkp`, or TESPy scripts).

- **Parsing method**: The appropriate method (:code:`from_aspen`, :code:`from_ebsilon` or :code:`from_tespy`) based on the simulation tool used.

- **Ambient Conditions (optional)**: Ambient temperature (:code:`Tamb`) and pressure (:code:`pamb`) if they are not defined within the simulation.

- **Chemical Exergy Library (optional)**: The library used for calculating chemical exergy. Currently only the Ahrendts model is supported.

Example:

.. code-block:: python

    from exerpy import ExergyAnalysis
    model_path = 'my_model.ebs'
    ean = ExergyAnalysis.from_ebsilon(model_path, chemExLib='Ahrendts')

The parsing process involves the following key steps:

    1. **Initialization and Simulation**: ExerPy initializes the model by connecting
    to the chosen simulation tool. If required, it runs the simulation to ensure all
    the latest data are available.

    2. **Data Extraction**: Extracts detailed information about components and connections,
    including properties like temperature, pressure, mass flow, enthalpy, and entropy.
    All data are converted to SI units for consistency.

    3. **Ambient Conditions**: Retrieves or sets ambient conditions (:code:`Tamb` and :code:`pamb`),
    essential for exergy calculations. These can be sourced from the model or specified
    by the user.

    4. **Physical Exergy Calculation**: Imports or calculates mechanical and thermal exergy values
    using the extracted properties. This ensures consistency in fluid property models between
    the simulation and exergy calculations.

    5. **Chemical Exergy Calculation**: Calculates chemical exergy based on material
    composition, utilizing the Ahrendts reference environment.


    6. **Data Storage**: Saves the parsed data and exergy calculations into a JSON
    file for subsequent analysis.

It is possible to provide a JSON file containing the connection and component data
in the appropriate structure and format. This file must include information on the physical
exergy values (mechanical and thermal), as ExerPy does not calculate them autonomously.
In this case, the method :code:`from_json` should be used to load the data. The chemical
exergy calculation is then performed based on this provided data and the
Ahrendts reference environment.

=======
Outputs
=======

The output of this first module is a JSON file containing all the extracted data
and calculated exergy values. This JSON file serves as the primary input for the
exergy analysis module.

******************
2. Exergy Analysis
******************

The exergy analysis module provides tools for evaluating system performance at both the component and system levels. Key capabilities include:

1. **Exergy Analysis of Components**: Evaluates the exergy destruction and efficiency of individual components within the system.
2. **Exergy Analysis of the Entire System**: Assesses the overall exergy balance, including the exergy of fuel, product, and losses, to determine system-wide efficiency and irreversibilities.

The method used to perform the exergy analysis is `analyse`. This method takes the
parsed data as input and conducts the component-level exergy analysis based on the specified parameters.

======
Inputs
======

The exergy analysis in ExerPy requires three structured inputs, each defined by a dictionary of connection IDs. These inputs represent the exergy flows associated with the fuel, product, and losses in the system. All connections entering or leaving the system must be specified, as they are essential for calculating the exergy balance.

- **Exergy of the fuel** (:code:`E_F`): 
    - ``inputs``: flows entering the system supplying exergy to the system used to obtain the product (e.g., fuel flow to a combustion chamber or a inlet flow of a hot stream)

    - ``outputs``: streams leaving the system diminishing the fuel exergy (e.g., outlet flow of a cold stream)

- **Exergy of the product** (:code:`E_P`): 
    - ``inputs``: flows leaving the system counted as useful output (e.g., the power flow from a generator)

    - ``outputs``: flows entering the system that reduce the net product (e.g., the power flow to a motor)

- **Exergy loss** (:code:`E_L`): 
    - ``inputs``: flows leaving the system and released to the environment (e.g., exhaust gases, cold outlet flow of a condenser in a steam cycle)

    - ``outputs``: flows entering the system that will later exit as losses (e.g., cold inlet flow of a condenser in a steam cycle)

.. code-block:: python

    from exerpy import ExergyAnalysis
    model_path = 'my_model.ebs'
    ean = ExergyAnalysis.from_ebsilon(model_path)

    fuel = {"inputs": ['1'], "outputs": ['3']}
    product = {"inputs": ['E1'], "outputs": ['E2']}
    loss = {"inputs": ['13'], "outputs": ['11']}

    ean.analyse(E_F=fuel, E_P=product, E_L=loss)

=======
Outputs
=======

The results of the exergy analysis can be printed to the console:

.. code-block:: python

    ean.exergy_results()

Alternatively, they can be stored in separate :code:`pandas.DataFrames` for further analysis:

.. code-block:: python

    df_comps, df_material_conns, df_non_material_conns = ean.exergy_results()

The results include the following key parameters:

    - Fuel exergy (:code:`E_F`) in kW
    - Product exergy (:code:`E_P`) in kW
    - Destruction exergy (:code:`E_D`) in kW
    - Loss exergy (:code:`E_L`) in kW
    - Exergy efficiency (:code:`ε`) in %
    - Exergy destruction ratio (:code:`y` and :code:`y_star`) in %

These values are provided both for each component and for the entire system.

**************
API References
**************

.. toctree::
    :maxdepth: 1
    :glob:

    api/analyses.rst
    api/components.rst
    api/functions.rst
    api/parser.rst
