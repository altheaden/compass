#!/usr/bin/env python

import parsl
from parsl.config import Config
from parsl.app.app import python_app
from parsl.providers import SlurmProvider
from parsl.launchers import SrunLauncher
from parsl.executors import WorkQueueExecutor
import time


# App that sleeps for given time and then returns time slept
@python_app
def generate(delay,
             parsl_resource_specification={'cores': 1,
                                           'memory': 100,
                                           'disk': 10}):
    import time
    time.sleep(delay)
    return delay


if __name__ == '__main__':

    # CHANGE if need be before running
    compass_branch = '/home/ac.althea/code/compass/parsl_res_test/'
    activation_script = 'load_dev_compass_1.0.0_chrysalis_intel_impi.sh'
    # Command to be run before starting a worker
    worker_init = f'source {compass_branch}/{activation_script}'

    config = Config(
        executors=[
            WorkQueueExecutor(
                label='Chrysalis_WQEX',
                # autolabel=True,  # Seems not to work very well
                autocategory=False,  # Set True if using autolabel
                shared_fs=True,
                provider=SlurmProvider(
                    partition='compute',  # Partition / QOS
                    nodes_per_block=1,
                    init_blocks=1,
                    worker_init=worker_init,
                    launcher=SrunLauncher(),
                    walltime='02:00:00'
                )
            )
        ]
    )

    # load the Parsl config 
    print("Loading config...")
    dfk = parsl.load(config)
    print("Config loaded.")

    # Run dummy test to allocate resources
    print("Begin dummy timer...")
    start_du = time.time()
    generate(0).result()
    total_du = time.time() - start_du
    print(f"Dummy finished in {total_du:.2f} seconds.")

    # Set delay and number of tasks
    delay = 15  # runtime per task in seconds
    num_tasks = 10

    # Call generate method with given delay
    print("Begin execution timer...")
    start_ex = time.time()
    tasks = []

    for x in range(num_tasks):
        tasks.append(generate(delay))

    # Wait for all apps to finish and report execution time
    outputs = [x.result() for x in tasks]
    total_ex = time.time() - start_ex
    print(
        f"{num_tasks} tasks finished in {total_ex:.2f} seconds, "
        f"{(total_ex - delay):.2f} seconds longer than optimal time."
    )

    # Display total time
    print(
        "Total tracked runtime on node is "
        f"{(total_du + total_ex):.2f} seconds."
    )

    dfk.cleanup()
    parsl.clear()
