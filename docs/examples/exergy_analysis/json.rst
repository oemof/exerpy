.. _examples_json_label:

*******************
Custom JSON Example
*******************

.. seealso::

    The method behind this example: :ref:`Exergy Analysis <exergy_analysis_label>`.

ExerPy can also analyse data from simulation software other than the directly
supported Ebsilon Professional, Aspen Plus, and TESPy. This guide explains how to
structure your data in a JSON file and use ExerPy's API to perform an exergy
analysis with external simulation data.

.. tip::

    The JSON format is also the interface every parser of ExerPy writes to. If you work with a
    simulation tool that is not supported yet and would like a dedicated parser for it, please
    `open an issue <https://github.com/oemof/exerpy/issues>`__ or
    `contact the developers <mailto:s.tomasinelli@tu-berlin.de>`__. Contributions are welcome:
    :ref:`Contribute <exerpy_development_what_label>` describes how to set up the development version
    and submit a pull request.

ExerPy requires the JSON file to have the following format:

.. code-block:: text

    {
        "components": {
            "ComponentClass1": {
                "CompName1": {
                    "name": "CompName1",
                    "parameter1": 0.95,
                    "parameter2": 0.98
                },
                "CompName2": {
                    "name": "CompName2",
                    "parameter1": 100000,
                    "parameter2": 0.98
                }
            },
            "ComponentClass2": {
                "CompName3": {
                    "name": "CompName3",
                    "parameter1": 1.0,
                    "parameter2": 50,
                    "parameter3": 120000
                }
            }
        },
        "connections": {
            "ConnectionName1": {
                "name": "ConnectionName1",
                "kind": "material",
                "source_component": "CompName1",
                "source_connector": 0,
                "target_component": "CompName2",
                "target_connector": 0,
                "m": 10,
                "m_unit": "kg / s",
                "T": 400,
                "T_unit": "K",
                "p": 200000,
                "p_unit": "Pa",
                "h": 180000,
                "h_unit": "J / kg",
                "s": 8000,
                "s_unit": "J / kgK",
                "e_PH": 350000.0,
                "e_PH_unit": "J / kg",
                "mass_composition": {
                    "AR": 0.012818275230660559,
                    "CO2": 0.0003974658986251336,
                    "H2O": 0.006335253437165987,
                    "N2": 0.7505149830789085,
                    "O2": 0.22993402235463978
                },
                "e_CH": 1200,
                "e_CH_unit": "J / kg",
                "E_PH": 45000,
                "E_CH": 15000,
                "E": 60000,
                "E_unit": "W"
            },
            "ConnectionName2": {
                ...
            }
        },
        "ambient_conditions": {
            "Tamb": 288.15,
            "Tamb_unit": "K",
            "pamb": 101300.0,
            "pamb_unit": "Pa"
        }
    }

Please ensure the following:

- The components should be grouped by their class (e.g., CombustionChamber,
  Compressor, Turbine).
- Each component and each connection should have a unique name.
- The connections must specify the source and target components and their
  respective connectors. See the dedicated
  `ExerPy documentation <https://exerpy.readthedocs.io/en/latest/api/components.html>`__
  for more details on the connectors of each component.
- If you want to split the physical exergy into thermal and mechanical parts,
  pass :code:`split_physical_exergy=True` to :code:`from_json` and make sure
  that the connections contain the :code:`e_M` and :code:`e_T` parameters.
  These values are not calculated by ExerPy but must be provided in the JSON
  file!
- If you want to use the chemical exergy library of Ahrendts, pass
  :code:`chemExLib="Ahrendts"` to :code:`from_json`.
- Ambient conditions (:code:`Tamb` and :code:`pamb`) must be provided in the
  JSON file.
- The units for all parameters should be SI units (K, Pa, kg/s, W) for
  consistency.



Example
=======

This is an example of how to perform an exergy analysis using ExerPy with a
custom JSON file. The example is based on a simple gas turbine cycle with a
compressor, a combustion chamber, a turbine and a generator. Its components carry only their
names, since their exergy balances follow from the connections.

JSON file:

.. literalinclude:: /../examples/exergy_analysis/json_example/example.json
    :language: json

Python file:

.. code-block:: python

    model_path = 'example.json'

    ean = ExergyAnalysis.from_json(model_path, split_physical_exergy=False)

    fuel = {
        "inputs": ['1', '3'],
        "outputs": []
    }

    product = {
        "inputs": ['E1'],
        "outputs": []
    }

    loss = {
        "inputs": ['5'],
        "outputs": []
    }

    ean.analyse(E_F=fuel, E_P=product, E_L=loss)
    ean.exergy_results()

Full code
=========

.. dropdown:: Full code of this example

    .. literalinclude:: /../examples/exergy_analysis/json_example/example_json.py
        :language: python
