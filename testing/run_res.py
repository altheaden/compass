#!/usr/bin/env python

import subprocess
import argparse
import os


parser = argparse.ArgumentParser(
    description='Run one resolution of cosine bell')
parser.add_argument("-m", "--mesh", dest="mesh",
                    help="The name of the MPAS mesh")

args = parser.parse_args()
mesh = args.mesh

os.chdir(f"{mesh}/mesh")
#cmd_args = "srun -c 1 -n 1 -N 1 --mem 10G --tasks-per-node 1 compass run".split()
print(f"{mesh}: mesh")
cmd_args = ["compass", "run"]
subprocess.check_call(cmd_args)

os.chdir(f"../init")
print(f"{mesh}: init")
cmd_args = ["compass", "run"]
subprocess.check_call(cmd_args)

os.chdir(f"../forward")
print(f"{mesh}: forward")
cmd_args = ["compass", "run"]
subprocess.check_call(cmd_args)

