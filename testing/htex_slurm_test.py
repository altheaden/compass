#!/usr/bin/env python

import parsl
from parsl.config import Config
from parsl.providers import SlurmProvider
from parsl.executors import HighThroughputExecutor


def main():
    compass_branch = '/home/ac.althea/code/compass/slurm_mockup/'
    activation_script = 'load_dev_compass_1.0.0_chrysalis_intel_impi.sh'
    # Command to be run before starting a worker
    worker_init = f'source {compass_branch}/{activation_script}'

    config = Config(
        executors=[
            HighThroughputExecutor(
                label='Chrysalis_HTEX',
                provider=SlurmProvider(
                    partition='compute',  # Partition / QOS
                    nodes_per_block=2,
                    init_blocks=1,
                    worker_init=worker_init,
                    walltime='00:10:00',
                    cmd_timeout=120
                )
            )
        ]
    )

    dfk = parsl.load(config)

    from parsl import bash_app

    @bash_app
    def mpi_hello(nodes, ranks, msg, stdout=parsl.AUTO_LOGNAME, stderr=parsl.AUTO_LOGNAME):
        cmd = f"srun -n {ranks} -N {nodes} mpi_hello hello {msg}"
        return cmd

    def print_file(filename):
        with open(filename) as f:
            print(f.read())

    futures = []
    # Launch a mix of single node and 2 node tasks
    for i in range(10):
        if i % 2 == 0:
            x = mpi_hello(1, 4, i)
        else:
            x = mpi_hello(2, 4, i)
        futures.append(x)

    # wait for everything
    for i in futures:
        print(i.result())
        print(i.stdout, print_file(i.stdout))


if __name__ == '__main__':
    main()
