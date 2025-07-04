.. _installation_and_setup_label:

######################
Installation and setup
######################

Following you find guidelines for the installation process for Linux and
Windows. ExerPy is a Python package, thus it requires you to have Python 3
installed.

**********************
Installation of ExerPy
**********************

.. tab-set::

   .. tab-item:: Linux

      **Installing Python 3**

      Most Linux distributions will have Python 3 in their repository. Use the
      specific software management to install it, if it is not yet installed.
      If you are using Ubuntu/Debian try executing the following code in your
      terminal:

      .. code:: console

         sudo apt-get install python3

      You can also download different versions of Python via
      https://www.python.org/downloads/.

      **Having Python 3 installed**

      We recommend installing ExerPy within a virtual Python environment and
      not into the base, system-wide Python installation. On Linux you can use
      virtualenv to do so.

      1. Install virtualenv using the package management of your Linux
         distribution, pip install or install it from source
         (`see virtualenv documentation <https://virtualenv.pypa.io/en/stable/installation.html>`_)
      2. Open terminal to create and activate a virtual environment by typing:

         .. code-block:: console

            virtualenv -p /usr/bin/python3 your_env_name
            source your_env_name/bin/activate

      3. In the active terminal type

         - if you plan to use json input only

         .. code-block:: console

            pip install exerpy

         - if you plan to use tespy

         .. code-block:: console

            pip install exerpy[tespy]

      Warning: If you have an older version of virtualenv you should update pip
      :code:`pip install --upgrade pip`.

      **Using Conda**

      Alternatively you can use conda for environment and package management.
      You can follow the installation instructions for Windows users.

   .. tab-item:: Windows

      For Windows we recommend using conda as package manager. You can download
      a lightweight open source variant of conda: 'miniforge3'.

      1. Download latest
         `miniforge3 <https://github.com/conda-forge/miniforge>`__ for Python
         3.x (64 or 32 bit).
      2. Install miniforge3
      3. Open 'miniforge prompt' to manage your virtual environments. You can
         create a new environment and acivate it by

         .. code-block:: console

            conda create -n exerpy-env python=3.12
            activate exerpy-env

      4. In the active prompt

         - if you plan to use json input only

         .. code-block:: console

            pip install exerpy

         - if you plan to use tespy

         .. code-block:: console

            pip install exerpy[tespy]

         - if you plan to use ebsilon

         .. code-block:: console

            pip install exerpy[ebsilon]

         - if you plan to use aspen

         .. code-block:: console

            pip install exerpy[aspen]

   .. tab-item:: Developer Version

      If you would like to get access to not yet released features or features
      under development you can install the developer version. The steps are
      similar to the steps here, but INSTEAD of installing ExerPy using

      .. code-block:: console

           pip install exerpy

      follow the instructions on
      :ref:`this page <exerpy_development_how_label>`.


**********************************
Additional Setup for Ebsilon Users
**********************************

To enable ExerPy to access Ebsilon Python program files, you need to set
an environment variable named ``EBS`` with the path to your Ebsilon
Python directory. This allows ExerPy to locate and import the necessary
Ebsilon modules. This is what you need to do if you are using Windows 11:

   1. Search and click on **Edit the system environment variables**.
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
define it as a user property in each model. Therefore, select the
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
Afterward, run the simulation and save it.
