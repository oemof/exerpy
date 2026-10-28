.. _json_format_label:

###########
JSON format
###########

ExerPy keeps a model in a JSON file. The parsers for TESPy, Ebsilon and Aspen write it with
:meth:`~exerpy.analyses.ExergyAnalysis.export_to_json`, and
:meth:`~exerpy.analyses.ExergyAnalysis.from_json` reads it back. You can also write such a file
yourself, for example to analyse a model from a simulator that ExerPy has no parser for. This
page describes the format and how ExerPy checks it.

*********
Structure
*********

A file has four sections:

.. list-table::
    :header-rows: 1
    :widths: 25 75

    * - Section
      - Content
    * - ``components``
      - The components, grouped by their type, e.g. ``Compressor`` or ``HeatExchanger``. Each
        component is stored under its name.
    * - ``connections``
      - The streams between the components, stored under their names.
    * - ``ambient_conditions``
      - The ambient temperature ``Tamb`` and pressure ``pamb``. Both may instead be passed to
        ``from_json``.
    * - ``settings``
      - Optional: ``split_physical_exergy`` and ``chemExLib``. Arguments passed to ``from_json``
        take precedence.

A compressor that takes in air and is driven by a motor outside the system looks like this:

.. code-block:: json

    {
        "components": {
            "Compressor": {
                "COMP": {"name": "COMP"}
            }
        },
        "connections": {
            "1": {
                "kind": "material",
                "source_component": null,
                "target_component": "COMP",
                "target_connector": 0,
                "m": 10.0, "T": 288.15, "p": 101300.0, "h": 15156.0, "e_PH": 0.0
            },
            "2": {
                "kind": "material",
                "source_component": "COMP",
                "source_connector": 0,
                "target_component": null,
                "m": 10.0, "T": 655.0, "p": 1551000.0, "h": 400000.0, "e_PH": 362000.0
            },
            "W1": {
                "kind": "power",
                "source_component": null,
                "target_component": "COMP",
                "target_connector": 1,
                "energy_flow": 3848440.0
            }
        },
        "ambient_conditions": {"Tamb": 288.15, "pamb": 101300.0},
        "settings": {"split_physical_exergy": false}
    }

**********
Components
**********

Every component needs its ``name``, which has to be the same as the key it is stored under.
Some types read further values:

.. list-table::
    :header-rows: 1
    :widths: 30 70

    * - Type
      - Further values
    * - ``HeatExchanger``
      - ``dissipative`` (``true`` or ``false`` to override the automatic choice), ``kA``, or
        ``kA`` inside ``parameters``
    * - ``SimpleHeatExchanger``
      - ``dissipative``, ``T_hot`` and ``T_cold``, the temperature of the heat source or
        consumer
    * - ``SteamGenerator``
      - ``T_hot``, the temperature of the heat source
    * - ``Mixer``, ``Splitter``
      - ``num_branches``, the number of identical parallel branches
    * - ``Heliostatfield``
      - ``Q_Solar``, the incident solar heat
    * - ``ParabolicTrough``
      - ``Q_Solar`` and ``num_branches``

All other values of a component, such as the efficiencies a simulator reports, are kept but not
checked.

***********
Connections
***********

``kind`` says what a connection carries: ``material``, ``power``, ``heat`` or ``other``.
Every connection names its ``source_component`` and ``target_component``. Use ``null`` where it
crosses the system boundary. ``source_connector`` and ``target_connector`` give the port of the
component, counted from 0.

.. list-table::
    :header-rows: 1
    :widths: 15 40 45

    * - Kind
      - Required
      - Optional
    * - ``material``
      - ``m``, ``T``, ``p``, ``h``, ``e_PH``
      - ``e_T`` and ``e_M`` (required with ``split_physical_exergy``), ``e_CH``, or
        ``mass_composition`` or ``molar_composition`` (required with ``chemExLib`` when ``e_CH``
        is not given), ``x``, ``v``
    * - ``power``
      - ``energy_flow``
      -
    * - ``heat``
      -
      - ``energy_flow``
    * - ``other``
      -
      -

ExerPy computes the exergy of each connection itself, so values such as ``E`` in an exported
file are not needed.

*****
Units
*****

ExerPy reads all values in SI units:

.. list-table::
    :header-rows: 1
    :widths: 50 50

    * - Value
      - Unit
    * - ``T``, ``Tamb``, ``T_hot``, ``T_cold``
      - K
    * - ``p``, ``pamb``
      - Pa
    * - ``m``
      - kg/s
    * - ``h``, ``e_PH``, ``e_T``, ``e_M``, ``e_CH``
      - J/kg
    * - ``energy_flow``, ``Q_Solar``
      - W
    * - ``kA``
      - W/K
    * - ``v``
      - m³/s
    * - ``x``, mass and molar fractions
      - dimensionless

**********
Validation
**********

``from_json`` checks the file before the analysis starts. The models parsed with ``from_tespy``,
``from_ebsilon`` and ``from_aspen`` are checked in the same way. The check finds for example
missing values, values of the wrong type, negative mass flows, unknown component types, two
streams entering the same port, and missing ``e_T`` and ``e_M`` when the physical exergy is
split. ExerPy reports all problems together, each with its place in the file:

.. code-block:: text

    Invalid ExerPy input (2 error(s)):
      - error: Expected `float` >= 0.0 - at `$.connections['1'].m`
      - error: Object missing required field `h` - at `$.connections['2']`

The error is a :class:`~exerpy.schema.InputValidationError`, a ``ValueError`` whose ``issues``
attribute lists every problem. Some findings are only warnings and are logged, for example mass
fractions that do not add up to one or a connection that is not attached to any component. Pass
``validate=False`` to skip the check.

A file can also be checked without running an analysis:

.. code-block:: python

    from exerpy.schema import validate

    with open("my_model.json", "rb") as file:
        validate(file.read())

A custom component declares the values it reads in a nested ``Input`` class, see
:class:`~exerpy.components.component.Component`. The check then covers it as well.

***********
JSON Schema
***********

:func:`~exerpy.schema.json_schema` returns the format as a `JSON Schema
<https://json-schema.org/>`__. Saved to a file, it lets an editor such as VS Code complete and
check a model while you write it:

.. code-block:: python

    import json

    from exerpy.schema import json_schema

    with open("exerpy_schema.json", "w") as file:
        json.dump(json_schema(), file, indent=4)
