import argparse
import sys
import os
import pickle
import configparser
import time
import glob

from mpas_tools.logging import LoggingContext
import mpas_tools.io
from compass.parallel import check_parallel_system, set_cores_per_node, \
    get_available_cores_and_nodes


def common_setup(test_case):  # todo: update docstring
    """Some setup common to running a test case, step or substep"""
    config = CompassConfigParser()
    config.add_from_file(test_case.config_filename)

    # todo: check parsl compatibility
    check_parallel_system(config)

    test_case.config = config
    set_cores_per_node(test_case.config)

    mpas_tools.io.default_format = config.get('io', 'format')
    mpas_tools.io.default_engine = config.get('io', 'engine')
