.. _exerpy_development_what_label:

####################
Contribute to exerpy
####################

What can I contribute?
**********************

ExerPy is developed as an open and free-to-use library by
`Sergio Tomasinelli, MSc. <https://github.com/sertomas>`__ at the Department of Energy and
Climate Protection, Technische Universität Berlin, under the supervision of Prof. Fontina Petrakopoulou.
The goal is to make the project widely accessible and to establish it as a community-driven
initiative in the future, as users may request special components or flexible
implementations of characteristics, or custom equations — basically, whatever the user
can think of.


You are invited to contribute to this process, share your ideas and experience
and perhaps even start developing the software. Your solutions may help other users as
well. Contributing to the development of ExerPy is straightforward and helps both the
development team and the wider user community. Developing
features is also a chance to engage in mutual code review and collaborate with other developers.

There are a variety of ways you can contribute to the development;
among others, these include:

Contribute to the documentation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
The easiest way to get involved in the developing process is by improving the
documentation. If you spot mistakes or think, the documentation could be more
precise or clearer in some sections, feel free to fix it and create a pull
request on the GitHub repository.

If you come across typos, grammatical mistakes or want to improve
the clarity of the documentation, make your adjustments or suggestions
and create a pull request for the dev branch. We appreciate your contribution!

Share your projects
^^^^^^^^^^^^^^^^^^^
Have you used the software in your research paper or project, or even in a
real world application? We would love to feature your project on our
:ref:`Example Applications <examples_label>` page. Please reach out to
us by opening a new issue on our GitHub page.

Report bugs or add new features
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
If you encounter bugs in the software, you are warmly invited to report them using
the issue tracker on the ExerPy GitHub page. Or, if you would like to suggest new features,
e.g., additional components or similar enhancements, you can also open a discussion in the
issue tracker. You are welcome to help develop missing features yourself if interested.

.. _exerpy_development_how_label:

How can I contribute?
*********************

You will find the most important information concerning the development process
in the following sections. If you have any further questions, feel free to
contact us. We look forward to hearing from you!

Install the developer version
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

It is recommended to use
`virtual environments <https://docs.python.org/3/tutorial/venv.html>`_ for
the development process. Fork the repository, clone your forked ExerPy GitHub
repository, and install the development requirements with pip.

.. code:: bash

    git clone https://github.com/YOUR_GITHUB_USERNAME/exerpy.git
    cd exerpy
    pip install -e .[dev]

To stay in sync with the oemof/exerpy base repository, add the link to
the oemof/exerpy repository as remote to your local copy of ExerPy. We will call
the remote "upstream". Fetch the available branches and after that, you can pull
changes from a specific branch of the oemof/exerpy repository (e.g., the "dev" branch in
the example below).

.. code:: bash

    git remote add upstream https://github.com/oemof/exerpy.git
    git fetch upstream
    git pull upstream dev --rebase

Use the :code:`--rebase` command to avoid merge commits for every upstream pull.
If you want to make changes to ExerPy, check out a new branch from your local dev
branch. Make your changes, commit them, and create a pull request on the oemof/exerpy dev
branch.

Collaboration with pull requests
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To collaborate, use the pull request functionality of GitHub as described here:
https://guides.github.com/activities/hello-world/

How to create a pull request
----------------------------

* Fork the oemof repository to your own GitHub account.
* Change, add or remove code.
* Commit your changes.
* Create a pull request and describe what you will do and why. Please use the
  pull request template we provide. It will appear when you click on
  "New pull request".
* Wait for approval.

.. _coding_requirements_label:

Generally, the following steps are required when changing, adding or removing code
----------------------------------------------------------------------------------

* Read the :ref:`style_guidlines_label` and :ref:`naming_conventions_label` and
  follow them.
* Add new tests according to what you have implemented.
* Update the documentation (for example, to reflect new features or API changes).
* Add a What's New entry and your name to the list of contributors.
* Check that all :ref:`tests_label` still work (see Tests).

.. _tests_label:

Tests
^^^^^

The tests in ExerPy are divided into two main parts:

* doc-tests (also used as examples for classes and methods/functions)
* software tests (defined in the tests folder).

The tests contain code examples that expect a specific outcome. If the outcome
matches the expectation, the test passes; if it differs, the test
fails. You can run the tests locally by navigating into your local GitHub clone.
The command :code:`check` tests PEP guidelines, the command :code:`docs`
tests the documentation build, and the command :code:`py3X` runs the
software tests in the selected Python version.

.. code:: bash

    python -m tox -e docs
    python -m tox -e check
    python -m tox -e py311
    python -m tox -e py312

If you want to have a look at the documentation build on your local machine use
the following command from the local ExerPy clone:

.. code:: bash

    python -m sphinx docs/ docs/_build

Additionally, all tests will run automatically when you push changes to a
branch that has a pull request opened.

If you have further questions regarding the tests, we encourage you to reach out to us.
We look forward to your inquiry.

.. _style_guidlines_label:

Issue-Management
^^^^^^^^^^^^^^^^

A good way to communicate with the development team is through issues on GitHub. If you
discover a bug, want to suggest an enhancement or have a question about a specific
development problem you’d like to discuss, please create an issue:

* Describe your point clearly and accurately
* Use the appropriate category tags from the list provided

Look at the existing issues to get an idea of how issues are used and structured.

Style guidelines
^^^^^^^^^^^^^^^^

We mostly follow standard guidelines rather than creating our own rules. So if
anything is not defined in this section, refer to a
`PEP rule <https://www.python.org/dev/peps/>`_ and follow it.

Docstrings
----------

We have adopted the numpydoc style for docstrings. See the following
link for more information:
`numpy docstrings <https://sphinxcontrib-napoleon.readthedocs.io/en/latest/example_numpy.html>`_.

Code commenting
---------------

Code comments include block and inline comments in the source code. They help
improve understanding of the code and should be used "as much as necessary, as little
as possible". When writing comments follow the
`PEP 0008 style guide <https://www.python.org/dev/peps/pep-0008/#comments>`_.

PEP8 (Python Style Guide)
-------------------------

* We adhere to `PEP8 <https://www.python.org/dev/peps/pep-0008/>`_ for all code
  produced in the framework.

* We use pylint to check your code. Pylint is integrated into many IDEs and
  Editors. `Check here <https://pylint.pycqa.org/en/latest/>`_ or ask the
  maintainer of your IDE or Editor

* Some IDEs have PEP8 checkers, which are very helpful, especially for python
  beginners.

.. _naming_conventions_label:

Naming Conventions
------------------

* We use plural names for modules if they contain more than one
  child class (e.g. :code:`import heat_exchangers` AND NOT
  :code:`import heat_exchanger`). If there are arrays in the code that hold
  multiple elements they must also be named in the plural.

* Please, follow the naming conventions of
  `pylint <http://pylint-messages.wikidot.com/messages:c0103>`_

* Use descriptive (“talking”) names

  * Variables/Objects: Name the after the data they represent
    (power\_line, wind\_speed)
  * Functions/Method: Name them after what they do: **use verbs**
    (get\_wind\_speed, set\_parameter)


Using git
^^^^^^^^^

Branching model
---------------

We mostly follow the Git branching model described by
`Vincent Driessen <https://nvie.com/posts/a-successful-git-branching-model/>`_.

Differences are:

* Instead of naming the  branch``origin/develop`` we use ``origin/dev``.
* Feature branches are named like ``features/*``
* Release branches are named like ``releases/*``

Commit message
--------------

Use this helpful `commit tutorial <https://commit.style/>`_ to
learn how to write clear and well structured commit messages.


Documentation
^^^^^^^^^^^^^

The general implementation-independent documentation, such as installation
guide, flow charts, and mathematical models, is written in ReStructuredText (rst).
The files can be found in the *docs*  folder. For more information on
ReStructuredText, see: https://docutils.sourceforge.io/rst.html.
