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
Interface (API) of ExerPy. The API is divided into three main modules:

1. **Parsing and Data Preparation**
2. **Exergy Analysis**
3. **Exergoeconomic Analysis**


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
    virtual machine. For Ebsilon Professional, a valid license including EBSOpen
    is required to enable the API connection. 


====================
Supported components
====================
ExerPy supports a wide range of components from the simulation tools. For Ebsilon Professional, the following components are supported:

.. autodata:: exerpy.parser.from_ebsilon.ebsilon_config.grouped_components
   :annotation:

For Aspen Plus, the supported components include:

.. autodata:: exerpy.parser.from_aspen.aspen_config.grouped_components
   :annotation:

For TESPy, the supported components include:

.. autodata:: exerpy.parser.from_tespy.tespy_config.EXERPY_TESPY_MAPPINGS
   :annotation:

We are continuously working to expand the list of supported components, so please refer to the latest documentation for updates.
In case you need to parse a component that is not yet supported, please contact us or open an issue on the GitHub repository.

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

.. note::

    **Solar thermal components (Ebsilon only).** The heliostat field, parabolic
    trough and solar tower are currently produced only by the Ebsilon parser
    (:code:`from_ebsilon`); the Aspen and TESPy parsers do not provide solar
    components. These componente receive their exergy from incoming solar radiation, 
    which the parser represents as a synthetic ``<name>_Q`` heat connection (there 
    is no ordinary inlet stream carrying it). To declare this solar input as fuel, 
    put the **name of the component** — not a connection name — in ``E_F["inputs"]``,
    e.g. ``{"inputs": ["SF"], "outputs": []}`` for a heliostat field named
    ``SF``. ExerPy resolves the component name to its ``<name>_Q`` connection
    automatically. The same applies if such a flow ever needs to appear in
    ``E_P`` or ``E_L``.

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
    - Exergy efficiency (:code:`epsilon`) in %
    - Exergy destruction ratio (:code:`y` and :code:`y_star`) in %

These values are provided both for each component and for the entire system.


****************************
3. Exergoeconomic Analysis
****************************

The exergoeconomic analysis module extends exergy analysis by allocating monetary costs to all exergy
streams in the system. It solves a linear equation system based on the SPECO method (Specific Exergy Costing)
to determine cost rates and specific costs for every connection and component.

.. note::

    Exergoeconomic analysis requires the exergy analysis to be performed with
    :code:`split_physical_exergy=True`, which separates thermal and mechanical exergy components.
    This is currently not available for Aspen Plus models.

======
Inputs
======

The exergoeconomic analysis requires the following inputs:

- **Completed ExergyAnalysis**: An :code:`ExergyAnalysis` instance with :code:`split_physical_exergy=True`
  on which :code:`analyse()` has already been called.

- **Cost dictionary**: A dictionary containing:

  - **Component investment costs**: :code:`"<component_name>_Z"` in currency/h (mandatory for all
    components except CycleCloser and PowerBus)
  - **Input stream costs**: :code:`"<connection_name>_c"` in currency/GJ (mandatory for all streams
    entering the system boundary)

.. code-block:: python

    from exerpy import ExergoeconomicAnalysis

    eco = ExergoeconomicAnalysis(ean)

    costs = {
        "COMP_Z": 80.0,   # Component investment cost [EUR/h]
        "CC_Z": 30.0,
        "1_c": 0.0,        # Input stream cost [EUR/GJ]
        "10_c": 10.0,
    }

    eco.run(costs)

=======
Outputs
=======

The results are retrieved using the :code:`exergoeconomic_results` method, which returns four
:code:`pandas.DataFrames`:

.. code-block:: python

    df_comp, df_mat_props, df_mat_costs, df_non_mat = eco.exergoeconomic_results()

The results include:

- **Component results**: Cost of fuel (:code:`C_F`), cost of product (:code:`C_P`),
  cost of exergy destruction (:code:`C_D`), investment cost rate (:code:`Z`),
  total cost (:code:`C_D+Z`), exergoeconomic factor (:code:`f`), and
  relative cost difference (:code:`r`)
- **Material connection costs**: Thermal (:code:`C_T`), mechanical (:code:`C_M`),
  chemical (:code:`C_CH`), and total (:code:`C_TOT`) cost rates with their specific costs
- **Non-material connection costs**: Total cost rate (:code:`C_TOT`) and specific cost (:code:`c_TOT`)
  for power and heat streams

Additionally, the :code:`evaluate_results` method identifies the components with the highest
cost improvement potential:

.. code-block:: python

    eco.evaluate_results(sort_by="C_D+Z", top_n=5)

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
