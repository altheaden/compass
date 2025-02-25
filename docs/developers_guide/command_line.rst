.. _dev_command_line:

Command-line interface
======================

The command-line interface for ``compass`` acts essentially like 5 independent
scripts: ``compass list``, ``compass setup``, ``compass clean`` and
``compass suite``, and ``compass run``.  These are the primary user interface
to the package, as described below.

When the ``compass`` package is installed into your conda environment, you can
run these commands as above.  If you are developing ``compass`` from a local
branch off of https://github.com/MPAS-Dev/compass, you will need to create a
conda environment appropriate for development (see :ref:`dev_conda_env`).
If you do, ``compass`` will be installed in the environment in "development"
mode, meaning you can make changes to the branch and they will be reflected
when you call the ``compass`` command-line tool.

.. _dev_compass_list:

compass list
------------

The ``compass list`` command is used to list test cases, test suites, and
supported machines.  The command-line options are:

.. code-block:: none

    compass list [-h] [-t TEST] [-n NUMBER] [--machines] [--suites] [-v]

By default, all test cases are listed:

.. code-block:: none

    $ compass list
    Testcases:
       0: examples/example_compact/1km/test1
       1: examples/example_compact/1km/test2
    ...

The number of each test case is displayed, followed by the relative path that
will be used for the test case in the work directory.

The ``-h`` or ``--help`` options will display the help message describing the
command-line options.

The ``-t`` or ``--test_expr`` flag can be used to supply a substring or regular
expression that can be used to list a subset of the tests.  Think of this as
as search expression within the default list of test-case relative paths.

The flags ``-n`` or ``--number`` are used to list the name (relative path) of
a single test case with the given number.

Instead of listing test cases, you can list all the supported machines that can
be passed to the ``compass setup`` and ``compass suite`` by using the
``--machines`` flag.

Similarly, you can list all the available test suites for all :ref:`dev_cores`
by using the ``--suites`` flag.  The result are the flags that would be passed
to ``compass suite`` as part of setting up this test suite.

The ``-v`` or ``--verbose`` flag lists more detail about each test case,
including its description, short name, core, configuration, subdirectory within
the configuration and the names of its steps:

.. code-block:: none

    $ compass list -n 0 -v
    path:          examples/example_compact/1km/test1
    description:   Tempate 1km test1
    name:          test1
    core:          examples
    configuration: example_compact
    subdir:        1km/test1
    steps:
     - step1
     - step2

.. _dev_compass_setup:

compass setup
-------------

The ``compass setup`` command is used to set up one or more test cases.

.. note::

    You must have built the executable for the standalone MPAS component you
    want to run before setting up a compass test case.

The command-line options are:

.. code-block:: none

    compass setup [-h] [-t PATH] [-n NUM [NUM ...]] [-f FILE] [-m MACH]
                  [-w PATH] [-b PATH] [-p PATH]

The ``-h`` or ``--help`` options will display the help message describing the
command-line options.

The test cases to set up can be specified either by relative path or by number.
The ``-t`` or ``--test`` flag is used to pass the relative path of the test
case within the resulting work directory.  The is the path given by
:ref:`dev_compass_list`.  Only one test case at a time can be supplied to
``compass setup`` this way.

Alternatively, you can supply the test numbers of any number of test cases to
the ``-n`` or ``--case_number`` flag.  Multiple test numbers are separated by
spaces (not commas like in :ref:`legacy_compass`).  These are the test numbers
given by :ref:`dev_compass_list`.

``compass setup`` requires a few basic pieces of information to be able to set
up a test case.  These include places to download and cache some data files
used in the test cases and the location where you built the MPAS model.  There
are a few ways to to supply these.  The ``-m`` -r ``--machine`` option is used
to tell ``compass setup`` which supported machine you're running on (leave this
off if you're working on an "unknown" machine).  See :ref:`dev_compass_list`
above for how to list the supported machines.

You can supply the directory where you have built the MPAS component with the
``-p`` or ``--mpas_model`` flag.  This can be a relative or absolute path.  The
default for the ``landice`` core is ``MALI-Dev/components/mpas-albany-landice``
and the default for the ``ocean`` core is
``E3SM-Project/components/mpas-ocean``.

You can also supply a config file with config options pointing to the
directories for cached data files, the location of the MPAS component, and much
more (see :ref:`config_files` and :ref:`setup_overview`).  Point to your config
file using the ``-f`` or ``--config_file`` flag.

The ``-w`` or ``--work_dir`` flags point to a relative or absolute path that
is the base path where the test case(s) should be set up.  The default is the
current directory.  It is recommended that you supply a work directory in
another location such as a temp or scratch directory to avoid confusing the
compass code with test cases setups and output within the branch.

To compare test cases with a previous run of the same test cases, use the
``-b`` or ``--baseline_dir`` flag to point to the work directory of the
previous run.  Many test cases validate variables to make sure they are
identical between runs, compare timers to see how much performance has changed,
or both.  See :ref:`dev_validation`.


.. _dev_compass_clean:

compass clean
-------------

The ``compass clean`` command is used to clean up one or more test cases,
removing the contents of their directories so there are no old files left
behind before a fresh call to :ref:`dev_compass_setup`. The command-line
options are:

.. code-block:: none

    compass clean [-h] [-t PATH] [-n NUM [NUM ...]] [-w PATH]

The ``-h`` or ``--help`` options will display the help message describing the
command-line options.

As with :ref:`dev_compass_setup`, the test cases to cleaned up can be specified
either by relative path or by number. The meanings of the ``-t`` or ``--test``,
``-n`` or ``--case_number``, and ``-w`` or ``--work_dir`` flags are the same
as in :ref:`dev_compass_setup`.

.. _dev_compass_suite:

compass suite
-------------

The ``compass suite`` command is used to set up a test suite. The command-line
options are:

.. code-block:: none

    compass suite [-h] -c CORE -t SUITE [-f FILE] [-s] [--clean] [-v]
                  [-m MACH] [-b PATH] [-w PATH] [-p PATH]

The ``-h`` or ``--help`` options will display the help message describing the
command-line options.

The required argument are ``-c`` or ``--core``, one of the :ref:`dev_cores`,
where the test suite and its test cases reside; and ``-t`` or ``--test_suite``,
the name of the test suite.  These are the options listed when you run
``compass list --suites``.

You must also specify whether you would like to set up the test suite
(``-s`` or ``--setup``), clean it up (``--clean``) or both.  If you choose to
clean up, the contents of each test case will be removed one by one before
(optionally) setting up each test case again.  Provenance for the test suite
such as previous output and the ``provenance`` file are retained and new
output is appended.  Manually delete the entire work directory if you would
like to start completely fresh.

As in :ref:`dev_compass_setup`, you can supply one or more of: a supported
machine with ``-m`` or ``--machine``; a path where you build MPAS model via
``-p`` or ``--mpas_model``; and a config file containing config options to
override the defaults with ``-f`` or ``--config_file``.  As with
:ref:`dev_compass_setup`, you may optionally supply a work directory with
``-w`` or ``--work_dir`` and/or a baseline directory for comparison with
``-b`` or ``--baseline_dir``.  If supplied, each test case in the suite that
includes :ref:`dev_validation` will be validated against the previous run in
the baseline.

.. _dev_compass_run:

compass run
-----------

The ``compass run`` command is used to run a test suite, test case or step
that has been set up in the current directory:

.. code-block:: none

    compass run [-h] [--steps STEPS [STEPS ...]]
                     [--no-steps NO_STEPS [NO_STEPS ...]]
                     [suite]

Whereas other ``compass`` commands are typically run in the local clone of the
compass repo, ``compass run`` needs to be run in the appropriate work
directory. If you are running a test suite, you may need to provide the name
of the test suite if more than one suite has been set up in the same work
directory (with or without the ``.pickle`` suffix that exists on the suite's
file in the working directory).  If you are in the work directory for a test
case or step, you do not need to provide any arguments.

If you want to explicitly select which steps in a test case you want to run,
you have two options.  You can either edit the ``steps_to_run`` config options
in the config file:

.. code-block:: cfg

    [test_case]
    steps_to_run = initial_state full_run restart_run

Or you can use ``--steps`` to supply a list of steps to run, or ``--no-steps``
to supply a list of steps you do not want to run (from the defaults given in
the config file).  For example,

.. code-block:: none

    python -m compass run --steps initial_state full_run

or

.. code-block:: none

    python -m compass run --no-steps restart_run

Would both accomplish the same thing in this example -- skipping the
``restart_run`` step of the test case.

.. note::

    If changes are made to ``steps_to_run`` in the config file and ``--steps``
    is provided on the command line, the command-line flags take precedence
    over the config option.
