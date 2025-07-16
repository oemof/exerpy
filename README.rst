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

.. figure:: https://raw.githubusercontent.com/oemof/exerpy/refs/heads/main/docs/_static/images/logo_exerpy_big.svg
    :align: center

************
Key Features
************

- **Comprehensive Exergy Analysis**: Calculate physical and chemical exergy, perform component-level and system-wide analysis.
- **Flexible Integration**: Compatible with multiple simulation tools (Ebsilon Professional, Aspen Plus, TESPy).
- **Advanced Component Library**: Pre-built components for common energy system elements (turbines, heat exchangers, etc.).
- **Extensible Architecture**: Easy-to-use framework for implementing custom components and analysis methods.
- **Robust Data Handling**: Consistent fluid property models and automated data extraction from simulation tools.
- **Open Source**: MIT licensed, free for academic and commercial use.

***************
Getting Started
***************

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

Custom json
-----------

.. code:: python

    from exerpy import ExergyAnalysis

    model_path = 'my_model.json'

    ean = ExergyAnalysis.from_json(model_path, chemExLib='Ahrendts')

    fuel = {"inputs": ['Fuel'], "outputs": []}
    product = {"inputs": ['Power'], "outputs": []}

    ean.analyse(E_F=fuel, E_P=product)
    ean.exergy_results()

Exported tespy model
--------------------

.. code:: python

    from exerpy import ExergyAnalysis

    model_path = 'tespy_model_export.json'

    ean = ExergyAnalysis.from_tespy(model_path, chemExLib='Ahrendts')

    fuel = {"inputs": ['Fuel'], "outputs": []}
    product = {"inputs": ['Power'], "outputs": []}

    ean.analyse(E_F=fuel, E_P=product)
    ean.exergy_results()

You can also use a tespy network object instead!

Ebsilon model
-------------

.. code:: python

    from exerpy import ExergyAnalysis

    model_path = 'my_model.ebs'

    ean = ExergyAnalysis.from_ebsilon(model_path, chemExLib='Ahrendts')

    fuel = {"inputs": ['Fuel'], "outputs": []}
    product = {"inputs": ['Power'], "outputs": []}

    ean.analyse(E_F=fuel, E_P=product)
    ean.exergy_results()

For more detailed tutorials and examples, see the
`online documentation <https://exerpy.readthedocs.io>`__.

********
Citation
********

If you use ExerPy in your scientific work, please consider citing it to support
ongoing development. You can cite ExerPy using the following BibTeX entry:

.. code::

    @software{ExerPy,
         author = {Tomasinelli, Sergio and Witte, Francesco and Müller, Robert},
         title = {{ExerPy}: Exergy Analysis in Python},
         note = {Supervision: Prof. Dr.-Ing. Fontina Petrakopoulou}
         url = {https://github.com/oemof/exerpy},
         version = {0.0.2},
         year = {2025}
    }

*******
License
*******

MIT License

Copyright (c) Sergio Tomasinelli

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
