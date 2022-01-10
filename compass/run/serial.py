import argparse
import sys
import os
import pickle
import time
import glob

from mpas_tools.logging import LoggingContext
from compass.logging import log_method_call
from compass.config import CompassConfigParser
from compass.parallel import check_parallel_system, \
    get_available_cores_and_nodes
from compass.run import common_setup


def run_tests(suite_name, quiet=False, is_test_case=False, steps_to_run=None,
              steps_not_to_run=None, print_substeps=False):
    """
    Run the given test suite or test case

    Parameters
    ----------
    suite_name : str
        The name of the test suite

    quiet : bool, optional
        Whether step names are not included in the output as the test suite
        progresses

    is_test_case : bool
        Whether this is a test case instead of a full test suite

    steps_to_run : list of str, optional
        A list of the steps to run if this is a test case, not a full suite.
        The default behavior is to run the default steps unless they are in
        ``steps_not_to_run``

    steps_not_to_run : list of str, optional
        A list of steps not to run if this is a test case, not a full suite.
        Typically, these are steps to remove from the defaults

    print_substeps : bool, optional
        Whether to print the names of substeps as the suite progresses.  Has no
        effect if ``quiet == True``.
    """
    # ANSI fail text: https://stackoverflow.com/a/287944/7728169
    start_fail = '\033[91m'
    start_pass = '\033[92m'
    start_time_color = '\033[94m'
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
    suite_config = CompassConfigParser()
    suite_config.add_from_file(config_filename)
    check_parallel_system(suite_config)

    # start logging to stdout/stderr
    with LoggingContext(suite_name) as logger:

        os.environ['PYTHONUNBUFFERED'] = '1'

        if not is_test_case:
            try:
                os.makedirs('case_outputs')
            except OSError:
                pass

        failures = 0
        cwd = os.getcwd()
        suite_start = time.time()
        test_times = dict()
        success = dict()
        for test_name in test_suite['test_cases']:
            test_case = test_suite['test_cases'][test_name]

            logger.info('{}'.format(test_name))

            test_name = test_case.path.replace('/', '_')
            if is_test_case:
                log_filename = None
                test_logger = logger
            else:
                log_filename = '{}/case_outputs/{}.log'.format(cwd, test_name)
                test_logger = None
            with LoggingContext(test_name, logger=test_logger,
                                log_filename=log_filename) as test_logger:
                if quiet:
                    # just log the step names and any failure messages to the
                    # log file
                    test_case.stdout_logger = test_logger
                    print_substeps = False
                else:
                    # log steps to stdout
                    test_case.stdout_logger = logger
                test_case.logger = test_logger
                test_case.log_filename = log_filename
                test_case.new_step_log_file = is_test_case
                test_case.print_substeps = print_substeps

                os.chdir(test_case.work_dir)

                common_setup(test_case)

                test_case.steps_to_run = _update_steps_to_run(
                    steps_to_run, steps_not_to_run, test_case.config,
                    test_case.steps)

                test_start = time.time()
                log_method_call(method=test_case.run, logger=test_logger)
                test_logger.info('')
                test_list = ', '.join(test_case.steps_to_run)
                test_logger.info(f'Running steps: {test_list}')
                try:
                    test_case.run()
                    run_status = success_str
                    test_pass = True
                except BaseException:
                    run_status = error_str
                    test_pass = False
                    test_logger.exception('Exception raised in run()')

                if test_pass:
                    test_logger.info('')
                    log_method_call(method=test_case.validate,
                                    logger=test_logger)
                    test_logger.info('')
                    try:
                        test_case.validate()
                    except BaseException:
                        run_status = error_str
                        test_pass = False
                        test_logger.exception('Exception raised in validate()')

                baseline_status = None
                internal_status = None
                if test_case.validation is not None:
                    internal_pass = test_case.validation['internal_pass']
                    baseline_pass = test_case.validation['baseline_pass']

                    if internal_pass is not None:
                        if internal_pass:
                            internal_status = pass_str
                        else:
                            internal_status = fail_str
                            test_logger.exception(
                                'Internal test case validation failed')
                            test_pass = False

                    if baseline_pass is not None:
                        if baseline_pass:
                            baseline_status = pass_str
                        else:
                            baseline_status = fail_str
                            test_logger.exception('Baseline validation failed')
                            test_pass = False

                status = '  test execution:      {}'.format(run_status)
                if internal_status is not None:
                    status = '{}\n  test validation:     {}'.format(
                        status, internal_status)
                if baseline_status is not None:
                    status = '{}\n  baseline comparison: {}'.format(
                        status, baseline_status)

                if test_pass:
                    logger.info(status)
                    success[test_name] = pass_str
                else:
                    logger.error(status)
                    logger.error('  see: case_outputs/{}.log'.format(
                        test_name))
                    success[test_name] = fail_str
                    failures += 1

                test_times[test_name] = time.time() - test_start

                secs = round(test_times[test_name])
                mins = secs // 60
                secs -= 60 * mins
                logger.info(f'  test runtime:        '
                            f'{start_time_color}{mins:02d}:{secs:02d}{end}')

        suite_time = time.time() - suite_start

        os.chdir(cwd)

        logger.info('Test Runtimes:')
        for test_name, test_time in test_times.items():
            secs = round(test_time)
            mins = secs // 60
            secs -= 60 * mins
            logger.info('{:02d}:{:02d} {} {}'.format(
                mins, secs, success[test_name], test_name))
        secs = round(suite_time)
        mins = secs // 60
        secs -= 60 * mins
        logger.info('Total runtime {:02d}:{:02d}'.format(mins, secs))

        if failures == 0:
            logger.info('PASS: All passed successfully!')
        else:
            if failures == 1:
                message = '1 test'
            else:
                message = '{} tests'.format(failures)
            logger.error('FAIL: {} failed, see above.'.format(message))
            sys.exit(1)


def run_step(print_substeps=False):
    """
    Used by the framework to run a step when ``compass run`` gets called in the
    step's work directory

    Parameters
    ----------
    print_substeps : bool, optional
        Whether to print the names of substeps as the suite progresses.  Has no
        effect if ``quiet == True``.
    """
    with open('step.pickle', 'rb') as handle:
        test_case, step = pickle.load(handle)
    test_case.steps_to_run = [step.name]
    test_case.new_step_log_file = False
    test_case.print_substeps = print_substeps

    common_setup(test_case)

    # start logging to stdout/stderr
    with LoggingContext(name=step.name) as logger:
        test_case.logger = logger
        test_case.stdout_logger = None
        test_case.run()
        test_case.validate()


def run_substep(substep_name):
    """
    Used by the framework to run a substep when ``compass run`` gets called in
    the step's work directory with a single substep requested

    Parameters
    ----------
    substep_name : str
        The name of a substep to run on its own
    """
    with open('step.pickle', 'rb') as handle:
        test_case, step = pickle.load(handle)

    common_setup(test_case)

    # start logging to stdout/stderr
    with LoggingContext(name=substep_name) as logger:
        test_case.logger = logger

        step.logger = logger

        step.runtime_setup()

        available_cores, _ = get_available_cores_and_nodes(test_case.config)
        # need to iterate over all substeps because some substeps make use of
        # resource constraints from other substeps
        for substep in step.substeps.values():
            substep.constrain_resources(available_cores)

        substep = step.substeps[substep_name]

        logger.info('')
        log_method_call(method=substep.run, logger=logger)
        logger.info('')
        substep.run()


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
    parser.add_argument("--print_substeps", dest="print_substeps",
                        action="store_true",
                        help="If set, substep names are included in the "
                             "output as the test suite progresses.")
    parser.add_argument("-q", "--quiet", dest="quiet", action="store_true",
                        help="If set, step names are not included in the "
                             "output as the test suite progresses.  Has no "
                             "effect when running test cases or steps on "
                             "their own.")
    args = parser.parse_args(sys.argv[2:])
    if args.quiet:
        args.print_substeps = False
    if args.suite is not None:
        run_tests(args.suite, quiet=args.quiet)
    elif os.path.exists('test_case.pickle'):
        run_tests(suite_name='test_case', quiet=args.quiet, is_test_case=True,
                  steps_to_run=args.steps, steps_not_to_run=args.no_steps,
                  print_substeps=args.print_substeps)
    elif os.path.exists('step.pickle'):
        if args.substep is None:
            run_step(print_substeps=args.print_substeps)
        else:
            run_substep(args.substep)
    else:
        pickles = glob.glob('*.pickle')
        if len(pickles) == 1:
            suite = os.path.splitext(os.path.basename(pickles[0]))[0]
            run_tests(suite, quiet=args.quiet,
                      print_substeps=args.print_substeps)
        elif len(pickles) == 0:
            raise OSError('No pickle files were found. Are you sure this is '
                          'a compass suite, test-case or step work directory?')
        else:
            raise ValueError('More than one suite was found. Please specify '
                             'which to run: compass run <suite>')


def _update_steps_to_run(steps_to_run, steps_not_to_run, config, steps):
    if steps_to_run is None:
        steps_to_run = config.get('test_case',
                                  'steps_to_run').replace(',', ' ').split()

    for step in steps_to_run:
        if step not in steps:
            raise ValueError(
                'A step "{}" was requested but is not one of the steps in '
                'this test case:\n{}'.format(step, list(steps)))

    if steps_not_to_run is not None:
        for step in steps_not_to_run:
            if step not in steps:
                raise ValueError(
                    'A step "{}" was flagged not to run but is not one of the '
                    'steps in this test case:'
                    '\n{}'.format(step, list(steps)))

        steps_to_run = [step for step in steps_to_run if step not in
                        steps_not_to_run]

    return steps_to_run

