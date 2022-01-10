import argparse
import sys
import os
import pickle
import configparser
import time
import glob
import parsl
from parsl.config import Config
from parsl.providers import SlurmProvider
from parsl.executors import HighThroughputExecutor
from parsl import python_app
from parsl import bash_app

from mpas_tools.logging import LoggingContext
import mpas_tools.io
from compass.parallel import check_parallel_system, set_cores_per_node
from compass.run import common_setup


def run_suite(suite_name):
    """
    Run the given test suite

    Parameters
    ----------
    suite_name : str
        The name of the test suite

    quiet : bool, optional
        Whether step names are not included in the output as the test suite
        progresses
    """
    # ANSI fail text: https://stackoverflow.com/a/287944/7728169
    start_fail = '\033[91m'
    start_pass = '\033[92m'
    end = '\033[0m'
    pass_str = '{}PASS{}'.format(start_pass, end)
    success_str = '{}SUCCESS{}'.format(start_pass, end)
    fail_str = '{}FAIL{}'.format(start_fail, end)
    error_str = '{}ERROR{}'.format(start_fail, end)

    # Allow a suite name to either include or not the .pickle suffix
    if suite_name.endswith('.pickle'):
        # code below assumes no suffix, so remove it
        suite_name = suite_name[:-len('.pickle')]
    # Now open the the suite's pickle file
    if not os.path.exists('{}.pickle'.format(suite_name)):
        raise ValueError('The suite "{}" doesn\'t appear to have been set up '
                         'here.'.format(suite_name))
    with open('{}.pickle'.format(suite_name), 'rb') as handle:
        test_suite = pickle.load(handle)

    # get the config file for the first test case in the suite
    test_case = next(iter(test_suite['test_cases'].values()))
    config_filename = os.path.join(test_case.work_dir,
                                   test_case.config_filename)
    suite_config = configparser.ConfigParser(
        interpolation=configparser.ExtendedInterpolation())
    suite_config.read(config_filename)
    check_parallel_system(suite_config)  # todo: check parsl compatibility

    # start logging to stdout/stderr
    with LoggingContext(suite_name) as stdout_logger:

        os.environ['PYTHONUNBUFFERED'] = '1'

        failures = 0
        cwd = os.getcwd()
        suite_start = time.time()
        test_times = dict()
        success = dict()
        for test_name in test_suite['test_cases']:

            # AppFuture basics to remember:
            # * All required modules must be imported within the app
            # * All objects passed as inputs or outputs to/from the app must be
            #   serializable (passed via pickle and cloudpickle)
            # * Apps cannot utilize global variables

            test_case = test_suite['test_cases'][test_name]

            stdout_logger.info(f"{test_name}")

            test_name = test_case.path.replace('/', '_')
            # todo: check logger logic
            # test_case.stdout_logger = stdout_logger  # todo: do we want this in parallel?
            test_case.stdout_logger = None  # todo: bad idea (?)
            test_case.logger = stdout_logger
            test_case.new_step_log_file = True  # Always True  in task parallel
            test_case.print_substeps = False    # Always False in task parallel todo: check (?)

            os.chdir(test_case.work_dir)

            common_setup(test_case)
            test_case.steps_to_run = test_case.config.get(
                'test_case', 'steps_to_run').replace(',', ' ').split()

            test_start = time.time()
            try:
                test_case.run()
                run_status = success_str
                test_pass = True
            except BaseException:
                run_status = error_str
                test_pass = False
                stdout_logger.exception('Exception raised in run()')

            if test_pass:
                with LoggingContext(
                        name="validation",
                        log_filename="validation.log") as valid_logger:
                    test_case.logger = valid_logger
                    try:
                        test_case.validate()
                    except BaseException:
                        run_status = error_str
                        test_pass = False
                        # todo: not sure if the logging is set up correctly,
                        # todo: wondering if it should be valid_logger here
                        # stdout_logger.exception(
                        #     'Exception raised in validate()')
                        valid_logger.exception(
                            'Exception raised in validate()')

            baseline_status = None
            internal_status = None
            if test_case.validation is not None:  # todo: fixed indent issues, check for possible other issues
                internal_pass = test_case.validation['internal_pass']
                baseline_pass = test_case.validation['baseline_pass']

                if internal_pass is not None:
                    if internal_pass:
                        internal_status = pass_str
                    else:
                        internal_status = fail_str
                        stdout_logger.exception(
                            'Internal test case validation failed')
                        test_pass = False

                if baseline_pass is not None:
                    if baseline_pass:
                        baseline_status = pass_str
                    else:
                        baseline_status = fail_str
                        stdout_logger.exception('Baseline validation failed')
                        test_pass = False

            status = '  test execution:      {}'.format(run_status)
            if internal_status is not None:
                status = '{}\n  test validation:     {}'.format(
                    status, internal_status)
            if baseline_status is not None:
                status = '{}\n  baseline comparison: {}'.format(
                    status, baseline_status)

            if test_pass:
                stdout_logger.info(status)
                success[test_name] = pass_str
            else:
                stdout_logger.error(status)
                stdout_logger.error(f'  see log files in: {test_case.path}')
                success[test_name] = fail_str
                failures += 1

            test_times[test_name] = time.time() - test_start

        # From here down : steps to take after all test cases complete
        suite_time = time.time() - suite_start

        os.chdir(cwd)

        stdout_logger.info('Test Runtimes:')
        for test_name, test_time in test_times.items():
            secs = round(test_time)
            mins = secs // 60
            secs -= 60 * mins
            stdout_logger.info('{:02d}:{:02d} {} {}'.format(
                mins, secs, success[test_name], test_name))
        secs = round(suite_time)
        mins = secs // 60
        secs -= 60 * mins
        stdout_logger.info('Total runtime {:02d}:{:02d}'.format(mins, secs))

        if failures == 0:
            stdout_logger.info('PASS: All passed successfully!')
        else:
            if failures == 1:
                message = '1 test'
            else:
                message = '{} tests'.format(failures)
            stdout_logger.error('FAIL: {} failed, see above.'.format(message))
            sys.exit(1)


def main():

    parser = argparse.ArgumentParser(
        description='Run a test suite, test case or step',
        prog='compass run')
    parser.add_argument("suite", nargs='?', default=None,
                        help="The name of a test suite to run. Can exclude "
                             "or include the .pickle filename suffix.")
    parser.add_argument("--steps", dest="steps", nargs='+', default=None,
                        help="The steps of a test case to run")
    parser.add_argument("--no-steps", dest="no_steps", nargs='+', default=None,
                        help="The steps of a test case not to run, see "
                             "steps_to_run in the config file for defaults.")
    parser.add_argument("--substep", dest="substep", default=None,
                        help="The substep of a step to run")
    # Task Parallel arguments
    parser.add_argument("-N", "--nodes", dest="nodes", type=int, metavar="N",
                        # required=True,  # todo: having both required & default seems redundant
                        help="The number of nodes to run on.")
    parser.add_argument("-t", "--walltime", dest="walltime", default=None,
                        metavar="HH:MM:SS",  # required=True,
                        help="The requested walltime in HH:MM:SS.")
    parser.add_argument("-p", "--partition", dest="partition", default=None,
                        # required=True,
                        help="The name of the partition to run on.")
    parser.add_argument("--qos", dest="qos", default=None,
                        help="The requested quality of service.")
    # todo: finish; Not sure what this option is for / what it's supposed to do
    parser.add_argument("--configuration", dest="configuration",
                        default=None,
                        help="Configuration.")
    parser.add_argument("-A", "--account", dest="account",
                        help="The Slurm account to charge resources to.")

    args = parser.parse_args(sys.argv[2:])
    # executor = _create_executor(partition=args.partition, nodes=args.nodes,
    #                      walltime=args.walltime)
    # dfk = parsl.load(executor)  # Parsl data flow kernel

    if args.suite is not None:
        run_suite(args.suite)
    elif os.path.exists('test_case.pickle'):  # todo: Issues when re-running test
        raise OSError("Not implemented for task parallel execution, run in "
                      "serial instead.")
    elif os.path.exists('step.pickle'):  # todo: Test
        raise OSError("Not implemented for task parallel execution, run in "
                      "serial instead.")
    else:
        pickles = glob.glob('*.pickle')
        if len(pickles) == 1:
            suite = os.path.splitext(os.path.basename(pickles[0]))[0]
            run_suite(suite)
        elif len(pickles) == 0:
            raise OSError('No pickle files were found. Are you sure this is '
                          'a compass suite, test-case or step work directory?')
        else:
            raise ValueError('More than one suite was found. Please specify '
                             'which to run: compass run <suite>')


def _create_executor(partition='compute', nodes=1, walltime='00:10:00',
                     account=None):
    """Create a Parsl executor"""
    compass_branch = '/home/ac.althea/code/compass/add_parsl/'
    activation_script = 'load_dev_compass_1.0.0_chrysalis_intel_impi.sh'
    # Command to be run before starting a worker
    worker_init = f'source {compass_branch}/{activation_script}'

    config = Config(
        executors=[
            HighThroughputExecutor(
                label='Chrysalis_HTEX',
                provider=SlurmProvider(
                    partition=partition,  # Partition / QOS
                    nodes_per_block=nodes,
                    init_blocks=1,
                    worker_init=worker_init,
                    walltime=walltime,
                    cmd_timeout=120,
                    account=account
                )
            )
        ]
    )

    # print(f"partition:          {partition}\n"
    #       f"nodes_per_block:    {nodes}\n"
    #       f"walltime:           {walltime}")

    parsl.clear()  # todo: necessary?
    return config
