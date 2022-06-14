#!/usr/bin/env python3

"""
    Bash App data future testing on local machine
"""

import shutil
import parsl
import os

from parsl.data_provider.files import File
from parsl.config import Config
from parsl.app.app import bash_app

from parsl.providers import LocalProvider
from parsl.providers import SlurmProvider
from parsl.executors import HighThroughputExecutor
from parsl.launchers import SrunLauncher


def main():
    parsl.clear()  # todo: usage/necessary? correct location?
    config = _create_executor('hpc')
    dfk = parsl.load(config)  # data flow kernel

    print("Config loaded")

    here = os.path.abspath(os.path.dirname(__file__))  # HPC compatible
    input_dir = os.path.join(here, 'inputs')
    output_dir = os.path.join(here, 'outputs')
    shutil.rmtree(input_dir, ignore_errors=True)
    os.mkdir(input_dir)  # input directory for all data files
    shutil.rmtree(output_dir, ignore_errors=True)
    os.mkdir(output_dir)  # output directory for all files

    # input_files = list()
    # output_files = list()

    data_futures = dict()

    # todo: dict with keys as filenames, vals as dfs

    for i in range(5):
        filename = os.path.join(input_dir, f'data_file_{i}.txt')
        data_futures[filename] = File(filename)
        with open(filename, 'w') as f:
            f.write("")
        # input_files.append(File(filename))
        # output_files.append(File(filename))

    print("Data files created")

    analysis_files = list()
    analysis_filename = os.path.join(output_dir, f'analysis.txt')
    with open(analysis_filename, "w") as f:
        f.write("")
    analysis_files.append(File(analysis_filename))
    # data_futures[analysis_filename] = File(analysis_filename)

    inputs = list()
    outputs = list()
    # inputs, outputs = data_futures.items()  # will not work

    print("Begin app chain")

    # first_app = first(inputs=list(inputs), outputs=list(outputs))
    # middle_app = middle(inputs=first_app.outputs, outputs=list(outputs))
    # last_app = last(inputs=middle_app.outputs,
    #                 outputs=analysis_files)
    last_app = last(list(data_futures.values()), analysis_files)

    print("Fetching result")
    # last_app.result()
    last_app.outputs[0].result()
    print("Finished")

    # todo: check usage/ordering of these
    dfk.cleanup()
    parsl.clear()


@bash_app
def first(inputs=[], outputs=[]):
    import time
    # Takes list of output files and appends to them
    commands = list()
    for (infile, outfile) in zip(inputs, outputs):
        # time.sleep(random.randint(0, 3))
        commands.append(f'cat {infile} >> {outfile}')
        commands.append(f'echo "first step complete" >> {outfile}')
    return ' && '.join(commands)


@bash_app
def middle(inputs=[], outputs=[]):
    import time
    # Takes list of output files and appends to them
    commands = list()
    for (infile, outfile) in zip(inputs, outputs):
        # time.sleep(random.randint(0, 3))
        commands.append(f'cat {infile} >> {outfile}')
        commands.append(f'echo "middle step complete" >> {outfile}')
    return ' && '.join(commands)


@bash_app
def last(inputs=[], outputs=[]):
    import time
    commands = list()
    analysis_file = outputs[0]
    for infile in inputs:
        # time.sleep(random.randint(0, 3))
        commands.append(f'cat {infile} >> {analysis_file}')
        commands.append(f'echo "analysis step complete" >> {analysis_file}')
    return ' && '.join(commands)


def _create_executor(type='loc'):
    config = None
    activation_script = os.environ['LOAD_COMPASS_ENV']
    # todo: first check if var exists, raise err if not: source load script!
    # Command to be run before starting a worker
    worker_init = f'source {activation_script}'

    if type == 'loc':
        config = Config(
            executors=[
                HighThroughputExecutor(
                    provider=LocalProvider()
                )])
    else:  # todo: anvil-specific options
        config = Config(
            executors=[HighThroughputExecutor(
                provider=SlurmProvider(
                    partition='acme-small',
                    walltime='01:00:00',
                    nodes_per_block=1,
                    init_blocks=1,
                    worker_init=worker_init,
                    launcher=SrunLauncher(),
                    cmd_timeout=120,
                    account='condo'
                )
            )]
        )
    return config


if __name__ == '__main__':
    main()
