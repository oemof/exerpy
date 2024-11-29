#################
API Documentation
#################

The ExerPy package offers a flexible, Python-based solution for conducting exergy 
analysis on energy-conversion systems. It supports integration with simulation tools 
like Ebsilon Professional, Aspen Plus, and TESPy, allowing users to extract detailed 
data about components and connections. The framework follows a structured workflow 
that includes data parsing, physical and chemical exergy calculations, and the 
generation of comprehensive exergy analysis results.

This section provides detailed information about the Application Programming 
Interface (API) of the ExerPy library. The API is divided into two main modules: 

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
    * - `Ebsilon Professional <https://www.ebsilon.com/de/>`_
      - A comprehensive tool for simulating and analyzing energy systems, particularly in the field of power plant engineering.
      - Commercial
      - 17.0
      - Windows
    * - `Aspen Plus <https://www.aspentech.com/en/products/engineering/aspen-plus>`_
      - A powerful process simulation software used for designing and optimizing chemical processes.
      - Commercial
      - 12.1
      - Windows
    * - `TESPy <https://tespy.readthedocs.io/en/main/>`_
      - A versatile Python package for simulating thermal energy systems.
      - Open Source
      - 0.7.7
      - Windows, macOS, Linux

.. note::

    Note that Ebsilon Professional and Aspen Plus require a valid commercial 
    license for use. Additionally, while these tools are designed only for 
    Windows, they can also be operated on macOS or Linus through the use of a 
    virtual machine.

======
Inputs
======

This module requires the user to provide the following inputs:

- **Simulation model**: The model file from the supported simulation tools (e.g., Ebsilon Professional :code:`.ebs`, Aspen Plus :code:`.bkp`, TESPy scripts). 

- **Parsing method**: The appropriate method (:code:`from_aspen`, :code:`from_ebsilon` or :code:`from_tespy`) based on the simulation tool used.

- **Ambient Conditions (optional)**: Ambient temperature (:code:`Tamb`) and pressure (:code:`pamb`) if they are not defined within the simulation model.

- **Chemical Exergy Library (optional)**: The library used for calculating chemical exergy. Currently only the Ahrendts model is supported.

Example:

.. code-block:: python

    >>> from exerpy import ExergyAnalysis
    >>> model_path = 'my_model.ebs'
    >>> ean = ExergyAnalysis.from_ebsilon(model_path, chemExLib='Ahrendts')

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

    5. **Chemical Exergy Calculation**: Computes chemical exergy based on material 
    composition, utilizing the Ahrendts reference environment. 

    6. **Data Storage**: Saves the parsed data and exergy calculations into a JSON 
    file for subsequent analysis.

It is possible to provide a JSON file containing the connection and component data 
in in the appropriate structure and format. This must include the information regarding the physical 
exergy values (mechanical and thermal), as ExerPy does not compute them autonomously. 
In this case, the mehtod :code:`from_json` should be used to load the data. The chemical 
exergy calculation is subsequently conducted based on this provided data and the 
Ahrendts reference environment.

=======
Outputs
=======

The output of this first module is a JSON file containing all the extracted data 
and calculated exergy values. This file serves as the primary input for the 
exergy analysis module.

******************
2. Exergy Analysis
******************

The exergy analysis module provides tools for evaluating system performance at both component and system levels. Key capabilities include:

    1. **Exergy Analysis of Components**: Evaluates the exergy destruction and efficiency of individual components within the system.
    2. **Exergy Analysis of the Entire System**: Assesses the overall exergy balance, including the exergy of fuel, product, and losses, to determine system-wide efficiency and irreversibilities.

The method for performing the exergy analysis is `analyse`. This method takes the 
parsed data as input and conducts the component exergy analysis based on the specified parameters.

======
Inputs
======

The exergy analysis requires the following inputs from the user:

- **Product exergy** (:code:`E_P`): Dictionary containing the connection IDs that define the product exergy flows. The connection IDs are specified as "inputs" (flows entering the system) and "outputs" (flows leaving the system).

- **Fuel exergy** (:code:`E_F`): Dictionary containing the connection IDs that define the fuel exergy flows, similarly structured with "inputs" and "outputs".

- **Loss exergy** (:code:`E_L`): Dictionary specifying the connection IDs for exergy losses. This is optional and defaults to an empty dictionary.

Example:

.. code-block:: python

    >>> from exerpy import ExergyAnalysis
    >>> model_path = 'my_model.ebs'
    >>> ean = ExergyAnalysis.from_ebsilon(model_path)

    >>> fuel = {"inputs": ['1'], "outputs": ['3']}
    >>> product = {"inputs": ['E1'], "outputs": ['E2']}
    >>> loss = {"inputs": ['13'], "outputs": ['11']}
    
    >>> ean.analyse(E_F=fuel, E_P=product, E_L=loss)

=======
Outputs
=======

The results of the exergy analysis can be printed to the console:

.. code-block:: python

    >>> ean.exergy_results()

Alternatively, they can be stored in separate :code:`pandas.DataFrames` for further analysis:

.. code-block:: python

    >>> df_comps, df_material_conns, df_non_material_conns = ean.exergy_results()

The results include the following key parameters:

    - Fuel exergy (:code:`E_F`) in kW
    - Product exergy (:code:`E_P`) in kW
    - Destruction exergy (:code:`E_D`) in kW
    - Loss exergy (:code:`E_L`) in kW
    - Exergy efficiency (:code:`ε`) in %
    - Exergy destruction ratio (:code:`y` and :code:`y_star`) in %

for each component and for the entire system. 


**************
API References
**************

.. toctree::
    :maxdepth: 1
    :glob:

    api/parser.rst
    api/analyses.rst
    api/components.rst


=====================================================
Helpers for documentation (delete before publishing):
=====================================================

- :py:class:`exerpy.analyses.ExergyAnalysis`: Main class for conducting exergy analysis
- :py:meth:`exerpy.analyses.ExergyAnalysis.analyse`: Method for performing the analysis
- :py:func:`exerpy.functions.convert_to_SI`: Utility function for unit conversion

- Internal link: :ref:`start page <exerpy_label>`
- Documentation: `ExerPy Documentation <https://exerpy.rtfd.io>`__