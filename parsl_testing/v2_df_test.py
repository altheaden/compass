#!/usr/bin/env python

"""
    Parsl DataFuture Test on HPC
"""

import shutil
import parsl
import os

from parsl.data_provider.files import File
from parsl.config import Config
from parsl.app.app import python_app
from parsl.providers import SlurmProvider
from parsl.launchers import SrunLauncher
from parsl.executors import WorkQueueExecutor


# Global vars - ONLY visible to non-parsl functions
USE_AUTO = True  # Controls values of autolabel and autocategory


def main():
    # CHANGE if need be before running
    compass_branch = '/home/ac.althea/code/compass/parsl_df_test/'
    activation_script = 'load_dev_compass_1.0.0_chrysalis_intel_impi.sh'
    # Command to be run before starting a worker
    worker_init = f'source {compass_branch}/{activation_script}'

    config = Config(
        executors=[
            WorkQueueExecutor(
                label='Chrysalis_WQEX',
                autolabel=USE_AUTO,
                autocategory=USE_AUTO,
                provider=SlurmProvider(
                    partition='compute',  # Partition / QOS
                    nodes_per_block=1,
                    init_blocks=1,
                    worker_init=worker_init,
                    launcher=SrunLauncher(),
                    scheduler_options='#SBATCH --job-name=ad.test',
                    walltime='02:00:00'
                )
            )
        ]
    )

    # load the Parsl config
    dfk = parsl.load(config)

    here = os.path.abspath(os.path.dirname(__file__))  # HPC compatible
    tempdir = os.path.join(here, 'temp')
    shutil.rmtree(tempdir, ignore_errors=True)
    os.mkdir(tempdir)  # Temp directory for all files

    tasks = {}

    for num in range(10):
        filename = os.path.join(tempdir, f'file_{num}.txt')
        data_filename = os.path.join(tempdir, f'data_file_{num}.txt')
        with open(filename, 'w') as f:
            f.write(f'{"data "*10}\n')  # very important scientific data
        tasks[num] = {'inputs': [File(filename)], 'outputs': [File(data_filename)]}

    data_futures = []

    for index, current in enumerate(tasks):
        tasks[current]['app_future'] = \
            import_data(delay=index, inputs=tasks[current]['inputs'],
                        outputs=tasks[current]['outputs'])
        data_futures.insert(index, tasks[current]['app_future'].outputs[0])

    results = [File(os.path.join(tempdir, "analysis.txt"))]
    analysis = analyze(inputs=data_futures, outputs=results)

    # print analysis
    with open(analysis.outputs[0].result(), 'r') as f:
        print(f.read())

    dfk.cleanup()
    parsl.clear()


"""
Create new files that have old data plus important new data
inputs and outputs lists are tied to import_data() function
"""
@python_app
def import_data(delay=0, inputs=[], outputs=[],
                parsl_resource_specification={'cores': 1,
                                              'memory': 100,
                                              'disk': 10}):
    import time
    time.sleep(delay)
    with open(inputs[0], 'r') as f, open(outputs[0], 'w') as df:
        for line in f:
            df.write(line)
        df.write(f'{"new data "*5}\n')
    return


"""
Analyze results somehow by concatenating them into one file
inputs and outputs lists are tied to analyze() function
"""
@python_app
def analyze(inputs=[], outputs=[],
            parsl_resource_specification={'cores': 1,
                                          'memory': 100,
                                          'disk': 10}):
    for num in range(len(inputs)):
        with open(inputs[num], 'r') as f, open(outputs[0], 'a') as a:
            a.write(f'{num+1}:\n')
            for line in f:
                a.write(f'\t{line}')
    return


if __name__ == '__main__':
    main()