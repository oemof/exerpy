#################################
ExerPy: Exergy Analysis in Python
#################################

ExerPy is a Python library and framework for automated exergy analysis of energy-conversion systems. It builds on the exergy analysis methodology
implemented in TESPy and extends its capabilities to seamlessly integrate
with simulation tools such as Ebsilon Professional, Aspen Plus, and TESPy itself.
ExerPy enables engineers and researchers to identify inefficiencies and optimize
the performance of thermodynamic systems through automated workflows and
consistent data handling.

With its advanced features, ExerPy accounts for both physical and chemical exergy, automates exergy balances, and
allows users to perform automated analysis of individual components and entire processes. This
helps identify where and why exergy losses occur, facilitating strategies to improve
efficiency, reduce costs, and support sustainable energy use.

.. image:: /_static/images/logo_exerpy_big.svg
   :align: center
   :class: only-light


.. image:: /_static/images/logo_exerpy_big_dark.svg
   :align: center
   :class: only-dark


************
Key Features
************

- **Automated, User-friendly Analysis**: Minimizes user input and enables automated exergy analysis with minimal human error.
- **Comprehensive Exergy Analysis**: Calculates physical and chemical exergies for both component- and system-level analyses.
- **Flexible Integration**: Compatible with multiple simulation tools (Ebsilon Professional, Aspen Plus, TESPy, and user-defined input; other software will be integrated in the future based on user feedback).
- **Advanced Component Library**: Pre-built components for common energy system elements (turbines, heat exchangers, etc.).
- **Extensible Architecture**: Easy-to-use framework for implementing custom components and analysis methods.
- **Robust Data Handling**: Consistent fluid property models and automated data extraction from simulation tools.
- **Open Source**: MIT licensed, free for academic and commercial use.


*********************
Getting Started
*********************

============
Installation
============
You can install the latest version of ExerPy using pip:

.. code:: bash

    pip install exerpy

===================
Quick Start Example
===================
Here's a simple example how to perform an exergy analysis using ExerPy:

.. code:: python

    from exerpy import ExergyAnalysis

    model_path = 'my_model.ebs'

    ean = ExergyAnalysis.from_ebsilon(model_path, chemExLib='Ahrendts')

    fuel = {"inputs": ['Fuel'], "outputs": []}
    product = {"inputs": ['Power'], "outputs": []}

    ean.analyse(E_F=fuel, E_P=product)
    ean.exergy_results()

For more detailed tutorials and examples, see the :ref:`User Guide <installation_and_setup_label>`.

********
Citation
********

If you use ExerPy in your scientific work, please cite it to support
ongoing development. Use the following BibTeX entry:

.. code::

    @software{ExerPy,
         author = {Your Name and Collaborators},
         title = {{ExerPy}: Exergy Analysis in Python},
         url = {https://github.com/tba},
         version = {0.0.1},
         year = {2024}
    }

*******
License
*******

.. include:: ../LICENSE
