#!/usr/bin/env python
"""
    Parsl DataFuture Test
"""
import shutil
import parsl
import os
from parsl.config import Config
from parsl.app.app import python_app
from parsl.providers import SlurmProvider
from parsl.launchers import SrunLauncher
from parsl.executors import WorkQueueExecutor
from parsl.data_provider.files import File


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
                shared_fs = True,
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
    os.mkdir(tempdir)  # Temp directory where outputs and inputs will be stored

    inputs = []
    outputs = []

    for num in range(10):
        filename = os.path.join(tempdir, f'file_{num}.txt')
        data_filename = os.path.join(tempdir, f'data_file_{num}.txt')
        with open(filename, 'w') as f:
            f.write("data " * 10)
        with open(data_filename, 'w') as df:
            df.write(" ")  # Seems like all files must exist first (?)
        inputs.append(File(filename))  # Must be Parsl File object (?)
        outputs.append(File(data_filename))

    for num in range(len(inputs)):
        data_files = import_data(num=num, inputs=inputs, outputs=outputs)

    with open(data_files.outputs[2].result(), 'r') as file:
        print(file.read())

    dfk.cleanup()
    parsl.clear()


@python_app
def import_data(num, inputs=[], outputs=[],
                parsl_resource_specification={'cores': 1,
                                              'memory': 100,
                                              'disk': 10}):
    with open(inputs[num], 'r') as f, open(outputs[num], 'w') as df:
        for line in f:
            df.write(line)
        df.write("new_data " * 5)
    # import time
    # time.sleep(15)
    return


if __name__ == '__main__':
    main()
