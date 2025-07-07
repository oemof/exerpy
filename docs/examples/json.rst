.. _examples_json_label:

*******************
Custom JSON Example
*******************

ExerPy can analyze data from simulation software that isn't directly supported (like Ebsilon Professional, Aspen Plus, or TESPy). This guide explains how to structure your data in a JSON file and use ExerPy's API to perform exergy analysis with external simulation data.

ExerPy requires specific data formatting in a JSON file. This is the required format:

.. code-block:: json

    {
        "components": {
            "ComponentClass1": {
                "CompName1": {
                    "name": "CompName1",
                    "parameter1": 0.95,
                    "parameter2": 0.98,
                },
                "ComponentClass2": {
                    "name": "CompName2",
                    "parameter1": 100000,   
                    "parameter2": 0.98,
                }
            },
            "ComponentClass2": {
                "CompName3": {
                    "name": "CompName3",
                    "parameter1": 1.0,
                    "parameter2": 50,
                    "parameter3": 120000,
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
                "h":180000,
                "h_unit": "J / kg",
                "s": 8000,
                "s_unit": "J / kgK",
                "e_PH": 350000.0,
                "e_PH_unit": "J / kg",
                "x": 1.0,
                "x_unit": "-",
                "mass_composition": {
                    "AR": 0.012818275230660559,
                    "CO2": 0.0003974658986251336,
                    "H2O": 0.006335253437165987,
                    "H2OG": 0.006335253437165987,
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
            },
        },
        "ambient_conditions": {
            "Tamb": 288.15,
            "Tamb_unit": "K",
            "pamb": 1013.0,
            "pamb_unit": "Pa"
        }
    }

Please ensure the following things:

- The components should be grouped by their class (e.g., CombustionChamber, Compressor, Turbine, etc.)
- Each component and each connection should have a unique name. 
- The connections must specify the source and target components and their respective connectors. Visit the dedicated `ExerPy documentation <file:///Z:/Desktop/exerpy/docs/_build/api/components.html>`_ for more details on the connectors of each component.
- If you want to split the physical exergy into thermal and mechanical parts, set :code:`"split_physical_exergy": true` in the Python code and make sure that the connections contain the :code:`e_M` and :code:`e_T` parameters. These values are not calculated by ExerPy, but must be provided in the JSON file!
- If you want to use the chemical exergy library of Ahrendts, set :code:`"chemExLib": "Ahrendts"` in the Python code.
- Ambient conditions (:code:`Tamb` and :code:`pamb`) must be provided in the JSON file.
- The units for all parameters should be SI units (K, bar, kg/s, kW) for consistency.



Example
=======

This is an example of how to perform an exergy analysis using ExerPy with a custom JSON file. The example is based on a simple gas turbine cycle with a combustion chamber, compressor, and generator.

JSON file:

.. code-block:: json

    {
        "components": {
            "CombustionChamber": {
                "CC": {
                    "name": "CC",
                    "eta_cc": 1.0,
                    "lamb": 2.971907640448107,
                    "A_unit": "m2",
                    "mass_flow_1": 637.8688906804568,
                    "mass_flow_1_unit": "W"
                }
            },
            "Compressor": {
                "COMP": {
                    "name": "COMP",
                    "eta_s": 0.9,
                    "eta_mech": 1.0
                }
            },
            "Generator": {
                "GEN1": {
                    "name": "GEN1",
                    "energy_flow_1": 251827804.941329
                }
            },
            "Turbine": {
                "GT": {
                    "name": "GT",
                    "eta_s": 0.92,
                    "eta_mech": 1.0,
                    "P": 493809952.3578626,
                    "P_unit": "W",
                    "mass_flow_1": 650.2399425410983
                }
            }
        },
        "connections": {
            "1": {
                "name": "1",
                "kind": "material",
                "source_component": null,
                "source_connector": null,
                "target_component": "COMP",
                "target_connector": 0,
                "m": 637.8688906804568,
                "m_unit": "kg / s",
                "T": 288.15,
                "T_unit": "K",
                "p": 101299.99999999999,
                "p_unit": "Pa",
                "h": 15156.141760290673,
                "h_unit": "J / kg",
                "s": 6869.754951010217,
                "s_unit": "J / kgK",
                "e_PH": 0.0,
                "e_PH_unit": "J / kg",
                "x": 1.0,
                "x_unit": "-",
                "mass_composition": {
                    "AR": 0.012818275230660559,
                    "CO2": 0.0003974658986251336,
                    "H2O": 0.006335253437165987,
                    "H2OG": 0.006335253437165987,
                    "N2": 0.7505149830789085,
                    "O2": 0.22993402235463978
                },
                "e_CH": 1149.2696774822346,
                "e_CH_unit": "J / kg",
                "E_PH": 0.0,
                "E_CH": 733083.3742682794,
                "E": 733083.3742682794,
                "E_unit": "W"
            },
            "2": {
                "name": "2",
                "kind": "material",
                "source_component": "COMP",
                "source_connector": 0,
                "target_component": "CC",
                "target_connector": 0,
                "m": 637.8688906804568,
                "m_unit": "kg / s",
                "T": 654.9662550204056,
                "T_unit": "K",
                "p": 1551000.0,
                "p_unit": "Pa",
                "h": 394516.46321819286,
                "h_unit": "J / kg",
                "s": 6929.305452009985,
                "s_unit": "J / kgK",
                "e_PH": 362200.8445948192,
                "e_PH_unit": "J / kg",
                "x": 1.0,
                "x_unit": "-",
                "mass_composition": {
                    "AR": 0.012818275230660559,
                    "CO2": 0.0003974658986251336,
                    "H2O": 0.006335253437165987,
                    "H2OG": 0.006335253437165987,
                    "N2": 0.7505149830789085,
                    "O2": 0.22993402235463978
                },
                "e_CH": 1149.2696774822346,
                "e_CH_unit": "J / kg",
                "E_PH": 231036650.94522184,
                "E_CH": 733083.3742682794,
                "E": 231769734.31949013,
                "E_unit": "W"
            },
            "3": {
                "name": "3",
                "kind": "material",
                "source_component": null,
                "source_connector": null,
                "target_component": "CC",
                "target_connector": 1,
                "m": 12.371051860641572,
                "m_unit": "kg / s",
                "T": 288.14999999999986,
                "T_unit": "K",
                "p": 1551000.0,
                "p_unit": "Pa",
                "h": 32680.856994852533,
                "h_unit": "J / kg",
                "s": 10125.423866937957,
                "s_unit": "J / kgK",
                "e_PH": 407487.22384831216,
                "e_PH_unit": "J / kg",
                "x": 1.0,
                "x_unit": "-",
                "mass_composition": {
                    "CH4": 1.0
                },
                "e_CH": 51384297.00551026,
                "e_CH_unit": "J / kg",
                "E_PH": 5041045.578776331,
                "E_CH": 635677803.0777769,
                "E": 640718848.6565533,
                "E_unit": "W"
            },
            "4": {
                "name": "4",
                "kind": "material",
                "source_component": "CC",
                "source_connector": 0,
                "target_component": "GT",
                "target_connector": 0,
                "m": 650.2399425410983,
                "m_unit": "kg / s",
                "T": 1423.1500491069728,
                "T_unit": "K",
                "p": 1500000.0,
                "p_unit": "Pa",
                "h": 1339186.0583581624,
                "h_unit": "J / kg",
                "s": 8044.6426189443055,
                "s_unit": "J / kgK",
                "e_PH": 1034298.1100852907,
                "e_PH_unit": "J / kg",
                "x": 1.0,
                "x_unit": "-",
                "mass_composition": {
                    "AR": 0.012574402873292333,
                    "CO2": 0.05258244644248185,
                    "H2O": 0.048944736526356544,
                    "H2OG": 0.048944736526356544,
                    "N2": 0.7362361620308293,
                    "O2": 0.1496622521270401
                },
                "e_CH": 6428.452268774877,
                "e_CH_unit": "J / kg",
                "E_PH": 672541943.6722261,
                "E_CH": 4180036.433876369,
                "E": 676721980.1061025,
                "E_unit": "W"
            },
            "5": {
                "name": "5",
                "kind": "material",
                "source_component": "GT",
                "source_connector": 0,
                "target_component": null,
                "target_connector": null,
                "m": 650.2399425410983,
                "m_unit": "kg / s",
                "T": 803.7714622065433,
                "T_unit": "K",
                "p": 103400.00009267079,
                "p_unit": "Pa",
                "h": 579758.7761335681,
                "h_unit": "J / kg",
                "s": 8129.874190039878,
                "s_unit": "J / kgK",
                "e_PH": 250311.35287950086,
                "e_PH_unit": "J / kg",
                "x": 1.0,
                "x_unit": "-",
                "mass_composition": {
                    "AR": 0.012574402861119481,
                    "CO2": 0.052582449047286525,
                    "H2O": 0.04894473865320185,
                    "H2OG": 0.04894473865320185,
                    "N2": 0.7362361613181042,
                    "O2": 0.14966224812028792
                },
                "e_CH": 6428.452786135837,
                "e_CH_unit": "J / kg",
                "E_PH": 162762439.71375123,
                "E_CH": 4180036.7702851305,
                "E": 166942476.48403636,
                "E_unit": "W"
            },
            "E1": {
                "name": "E1",
                "kind": "power",
                "source_component": "GEN1",
                "source_connector": 0,
                "target_component": null,
                "target_connector": null,
                "energy_flow": 248050387.8672091,
                "energy_flow_unit": "W",
                "E": 248050387.8672091,
                "E_unit": "W"
            },
            "W1": {
                "name": "W1",
                "kind": "power",
                "source_component": "GT",
                "source_connector": 1,
                "target_component": "COMP",
                "target_connector": 3,
                "energy_flow": 241982147.4165336,
                "energy_flow_unit": "W",
                "E": 241982147.4165336,
                "E_unit": "W"
            },
            "W2": {
                "name": "W2",
                "kind": "power",
                "source_component": "GT",
                "source_connector": 2,
                "target_component": "GEN1",
                "target_component_type": 11,
                "target_connector": 0,
                "energy_flow": 251827804.941329,
                "energy_flow_unit": "W",
                "E": 251827804.941329,
                "E_unit": "W"
            }
        },
        "ambient_conditions": {
            "Tamb": 288.15,
            "Tamb_unit": "K",
            "pamb": 1013.0,
            "pamb_unit": "Pa"
        }
    }


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
