#!/usr/bin/env python

"""
    Parsl DataFuture Test on HPC
    Specifically concerning chdir()
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

    inputs = []   # main() lists for housing data futures
    outputs = []  # parsl files only mutate their own copies

    orig_files = os.path.join(os.getcwd(), 'input_files')
    shutil.rmtree(orig_files, ignore_errors=True)
    os.mkdir(orig_files)  # Temp directory for all files

    for num in range(10):
        filename = os.path.join(orig_files, f'file_{num}.txt')
        data_filename = f'data_file_{num}.txt'
        with open(filename, 'w') as f:
            f.write(f'{"data "*10}\n')  # very important scientific data
        inputs.append(File(filename))
        outputs.append(File(data_filename))  # must be Parsl File objects

    # call import_data() sending Files for input and output
    for num in range(len(inputs)):
        data_files = import_data(num=num, inputs=inputs, outputs=outputs)

    # output Files are DataFutures until they are completed
    inputs = data_files.outputs
    outputs[0] = File("analysis.txt")
    # use main() outputs/inputs lists for readability (?)
    analysis = analyze(inputs=inputs, outputs=outputs)

    # print analysis
    with open(analysis.outputs[0].result(), 'r') as f:
        print(f.read())

    dfk.cleanup()
    parsl.clear()


"""
Create new files that have old data plus important new data
"""
@python_app
def import_data(num, inputs=[], outputs=[],
                parsl_resource_specification={'cores': 1,
                                              'memory': 100,
                                              'disk': 10}):
    import os
    orig_dir = os.getcwd()
    work_dir = os.path.join(orig_dir, f'folder_{num}.txt')
    shutil.rmtree(work_dir, ignore_errors=True)
    os.mkdir(work_dir)
    os.chdir(work_dir)

    outputs[num] = File(os.path.join(work_dir, outputs[num]))

    with open(inputs[num], 'r') as f, open(outputs[num], 'w') as df:
        for line in f:
            df.write(line)
        df.write(f'{"new data "*5}\n')

    os.chdir(orig_dir)
    return


"""
Analyze results somehow by concatenating them into one file
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
