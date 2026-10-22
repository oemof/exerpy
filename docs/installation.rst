.. _installation_and_setup_label:

######################
Installation and setup
######################

This page gives guidelines for installing ExerPy on Linux and
Windows. ExerPy is a Python package, so it requires you to have Python 3
installed.

**********************
Installation of ExerPy
**********************

.. tab-set::

   .. tab-item:: Linux

      **Installing Python 3**

      Most Linux distributions provide Python 3 in their repositories. On Ubuntu or Debian, install it
      together with its :code:`venv` module by running:

      .. code:: console

         sudo apt-get install python3 python3-venv

      Other versions of Python are available from https://www.python.org/downloads/.

      **Installing ExerPy in a virtual environment**

      We recommend installing ExerPy in a virtual environment rather than in the system-wide Python
      installation. The :code:`venv` module of Python creates one.

      1. Open a terminal in your project folder, then create and activate a virtual environment named
         :code:`.venv`:

         .. code-block:: console

            python3 -m venv .venv
            source .venv/bin/activate

      2. Update pip:

         .. code-block:: console

            python -m pip install --upgrade pip

      3. Install ExerPy with the extras you need:

         - with JSON input only

           .. code-block:: console

              pip install exerpy

         - with TESPy models

           .. code-block:: console

              pip install exerpy[tespy]

         - with cost estimates from the correlations of OpenPyTEA

           .. code-block:: console

              pip install exerpy[costs]

         - with Sankey and waterfall diagrams

           .. code-block:: console

              pip install exerpy[viz]

         Several extras can be combined, for example :code:`pip install exerpy[tespy,costs]`.

   .. tab-item:: Windows

      **Installing Python 3**

      Download and install Python 3 from https://www.python.org/downloads/.

      **Installing ExerPy in a virtual environment**

      We recommend installing ExerPy in a virtual environment rather than in the system-wide Python
      installation. The :code:`venv` module of Python creates one.

      1. Open a command prompt in your project folder, then create and activate a virtual environment
         named :code:`.venv`:

         .. code-block:: console

            py -m venv .venv
            .venv\Scripts\activate

      2. Update pip:

         .. code-block:: console

            python -m pip install --upgrade pip

      3. Install ExerPy with the extras you need:

         - with JSON input only

           .. code-block:: console

              pip install exerpy

         - with TESPy models

           .. code-block:: console

              pip install exerpy[tespy]

         - with Ebsilon Professional models

           .. code-block:: console

              pip install exerpy[ebsilon]

         - with Aspen Plus models

           .. code-block:: console

              pip install exerpy[aspen]

         - with cost estimates from the correlations of OpenPyTEA

           .. code-block:: console

              pip install exerpy[costs]

         - with Sankey and waterfall diagrams

           .. code-block:: console

              pip install exerpy[viz]

         Several extras can be combined, for example :code:`pip install exerpy[tespy,costs]`.

      **Using conda**

      Conda environments work as well. In a conda prompt, create and activate one, then install
      ExerPy with pip as in step 3:

      .. code-block:: console

         conda create -n exerpy python=3.12
         conda activate exerpy

   .. tab-item:: Developer Version

      If you would like access to features that are not yet released or still
      under development, you can install the developer version. The steps are
      similar to the ones above, but INSTEAD of installing ExerPy using

      .. code-block:: console

           pip install exerpy

      follow the instructions on
      :ref:`this page <exerpy_development_how_label>`.


**********************************
Additional Setup for Ebsilon Users
**********************************

To enable ExerPy to access the Ebsilon Python program files, you need to set
an environment variable named ``EBS`` with the path to your Ebsilon
Python directory. This allows ExerPy to locate and import the necessary
Ebsilon modules. This is what you need to do if you are using Windows 11:

   1. Search for and click on **Edit the system environment variables**.
   2. Click on **Advanced**.
   3. Click on **Environment Variables**.
   4. Under **User variables**, click **New**.
   5. Set the variable name to ``EBS`` and the variable value to the path of
      your Ebsilon Python files, for example:
      ``C:\Program Files\Ebsilon\EBSILONProfessional 17\Data\Python``

Be sure to replace the path with the actual location of your Ebsilon
Python directory. After setting the environment variable, restart your
terminal or IDE to ensure the changes take effect.

*************************************
Additional Setup for Aspen Plus Users
*************************************

Aspen Plus does not calculate physical exergy by default. Instead, you must
define it as a user property in each model. To do so, select the
:code:`Calculation Options` tab in the :code:`Setup` folder in the
:code:`Simulation` menu on the left. In the :code:`Calculations` tab, you will
see two fields titled :code:`Exergy reference environment temperature` and
:code:`Exergy reference environment pressure`. Enter the desired values for the
exergy analysis.

Then, select :code:`Property Sets` from the :code:`Simulation` menu on the left.
In the :code:`Properties` tab, click the :code:`Search` button. Search for the
:code:`EXERGYMS` entry and add it. In the :code:`Units` column next to the
:code:`Physical Properties` column, set :code:`J/kg` as the unit.

Next, select the :code:`Report Options` tab from the :code:`Setup` folder in
the :code:`Simulation` menu on the left. Select the :code:`Stream` tab on the
right and click the :code:`Property Sets` button. Move :code:`EXERGYMS` from
:code:`Available property sets` to :code:`Selected property sets` and confirm.
Afterwards, run the simulation and save it.
