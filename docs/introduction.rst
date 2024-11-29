#################################
ExerPy: Exergy Analysis in Python
#################################

ExerPy is a Python library designed to perform detailed exergy analysis of 
energy conversion systems. It builds on the exergy analysis methodology 
implemented in TESPy, while extending its capabilities to seamlessly integrate 
with simulation tools such as Ebsilon Professional, Aspen Plus, and TESPy itself. 
ExerPy enables engineers and researchers to identify inefficiencies and optimize 
the performance of thermodynamic systems through automated workflows and 
consistent data handling.

With its advanced features, ExerPy calculates both physical and chemical exergy, 
allowing users to analyze both individual components and entire systems. This 
helps to identify where and why exergy losses occur, facilitating strategies to improve 
efficiency, reduce costs, and support sustainable energy usage.

.. image:: /_static/images/logo_exerpy_big.svg
   :align: center
   :class: only-light


.. image:: /_static/images/logo_exerpy_big_dark.svg
   :align: center
   :class: only-dark


************
Key Features
************

- **Comprehensive Exergy Analysis**: Calculate physical and chemical exergy, perform component-level and system-wide analysis.
- **Flexible Integration**: Compatible with multiple simulation tools (Ebsilon Professional, Aspen Plus, TESPy).
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

If you use ExerPy in your scientific work, please consider citing it to support 
ongoing development. You can cite ExerPy using the following BibTeX entry:

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