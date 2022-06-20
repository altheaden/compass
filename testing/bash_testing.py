#!/usr/bin/env python3

"""
    Bash App general testing
"""
import random
import shutil
import parsl
import os

from parsl.data_provider.files import File
from parsl.config import Config
from parsl.app.app import bash_app
from parsl.providers import LocalProvider
from parsl.executors import HighThroughputExecutor
from parsl.providers import SlurmProvider
from parsl.launchers import SrunLauncher


def main():
    parsl.clear()  # todo: usage/necessary? correct location?
    config = _create_executor()
    dfk = parsl.load(config)  # data flow kernel

    print("config loaded")

    # hello_apps = list()
    #
    # for i in range(10):
    #     hello_apps.append(hello_world(i))
    #
    # for i in range(len(hello_apps)):
    #     hello_apps[i].result()

    print("start app")
    app = echo_hello()
    print("get result")
    app.result()

    print("read file")

    with open(app.stdout, 'r') as f:
        print(f.read())

    dfk.cleanup()
    parsl.clear()


# @bash_app
# def hello_world(identifier, stdout='out.txt'):
#     import time
#     time.sleep(random.randint(0, 5))
#     return f'echo "Hello, world! This is {identifier}."'


@bash_app
def echo_hello(stderr='std.err', stdout='std.out'):
    return 'echo "Hello World!"'


def _create_executor():
    activation_script = os.environ['LOAD_COMPASS_ENV']
    worker_init = f'source {activation_script}'
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
