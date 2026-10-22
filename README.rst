.. Keep this file in sync with docs/introduction.rst.

#################################
ExerPy: Exergy Analysis in Python
#################################

ExerPy is a Python library and framework for automated exergy analysis of energy-conversion systems.
It is developed at the
`Chair of Energy Engineering and Climate Protection <https://www.tu.berlin/en/energietechnik>`__,
Institute of Energy Engineering, Technische Universität Berlin, and builds on the exergy analysis
originally developed in `TESPy <https://github.com/oemof/tespy>`__. It integrates seamlessly with
simulation tools such as Ebsilon Professional, Aspen Plus and TESPy. ExerPy helps engineers and researchers identify
inefficiencies and improve the performance of thermodynamic systems through automated workflows and
consistent data handling.

ExerPy accounts for both physical and chemical exergy, automates the exergy balances and analyses
individual components as well as entire processes. This shows where and why exergy is destroyed and
lost, which helps to improve efficiency, reduce costs and support sustainable energy use. On top of
the exergy analysis, an exergoeconomic analysis assigns costs to every stream and component.

This release has been tested with TESPy 0.11.3, Ebsilon Professional 17 and Aspen Plus 14.5.

ExerPy is part of the Open Energy Modelling Framework `oemof <https://oemof.org/>`_.

.. figure:: https://raw.githubusercontent.com/oemof/exerpy/refs/heads/main/docs/_static/images/logo_exerpy_big.svg
    :align: center

************
Key Features
************

- **Automated, User-friendly Analysis**: Little user input, automated exergy balances and fewer
  sources of human error.
- **Comprehensive Exergy Analysis**: Physical and chemical exergy, at the level of the components and
  of the whole system.
- **Exergoeconomic Analysis**: Cost rates of every stream and component, from purchased equipment
  costs that are known, scaled from a reference, computed with user-defined cost equations or estimated
  with the correlations of OpenPyTEA.
- **Flexible Integration**: Models from Ebsilon Professional, Aspen Plus, TESPy and user-defined JSON
  input; other software can be added based on user feedback.
- **Component Library**: Pre-built components for common energy system elements (turbines, heat
  exchangers, etc.).
- **Extensible Architecture**: A framework for implementing custom components and analysis methods.
- **Robust Data Handling**: Consistent fluid property models and automated data extraction from
  simulation tools.
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

For complete installation instructions, see the `installation guide <https://exerpy.readthedocs.io/en/latest/installation.html>`__.

===================
Quick Start Example
===================

Here are simple examples of how to perform an exergy analysis using ExerPy:

Custom JSON
-----------

.. code:: python

    from exerpy import ExergyAnalysis

    model_path = 'my_model.json'

    ean = ExergyAnalysis.from_json(model_path, chemExLib='Ahrendts')

    fuel = {"inputs": ['Fuel'], "outputs": []}
    product = {"inputs": ['Power'], "outputs": []}

    ean.analyse(E_F=fuel, E_P=product)
    ean.exergy_results()

Exported TESPy model
--------------------

.. code:: python

    from exerpy import ExergyAnalysis

    model_path = 'tespy_model_export.json'

    ean = ExergyAnalysis.from_tespy(model_path, chemExLib='Ahrendts')

    fuel = {"inputs": ['Fuel'], "outputs": []}
    product = {"inputs": ['Power'], "outputs": []}

    ean.analyse(E_F=fuel, E_P=product)
    ean.exergy_results()

You can also pass a TESPy network object instead.

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

For more detailed tutorials and examples, see the `example applications <https://exerpy.readthedocs.io/en/latest/examples.html>`__.

********
Citation
********

If you use ExerPy in your scientific work, please cite it to support its ongoing development. Use the
following BibTeX entry:

.. code::

    @software{ExerPy,
         author = {Tomasinelli, Sergio and Witte, Francesco and Müller, Robert},
         title = {{ExerPy}: Exergy Analysis in Python},
         note = {Supervision: Prof. Dr.-Ing. Fontina Petrakopoulou},
         url = {https://github.com/oemof/exerpy},
         version = {0.2.0},
         year = {2026}
    }

*******
License
*******

MIT License

Copyright (c) Technische Universität Berlin, Chair of Energy Engineering and Climate Protection, and the ExerPy contributors

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
