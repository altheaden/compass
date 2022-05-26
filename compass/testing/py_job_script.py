#!/usr/bin/env python

import subprocess
from subprocess import Popen


def main():
    srun_call = 'srun -c 1 -n 1 -N 1 --mem 10G --tasks-per-node 1'

    jobs = ['./sleep_job.py 5 0',
            './sleep_job.py 5 1',
            './sleep_job.py 15 2']

    processes = list()

    for job in jobs:
        cmd_args = \
            f'{srun_call} {job}'.split()
        processes.append(Popen(cmd_args))

    while len(processes) > 0:
        for p in processes:
            if p.poll() is not None:
                processes.remove(p)  # todo: do we need to do anything with p?


if __name__ == '__main__':
    main()
