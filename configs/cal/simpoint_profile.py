import argparse
import sys
import os
import shutil

import m5
from m5.defines import buildEnv
from m5.objects import *
from m5.params import NULL
from m5.util import addToPath, fatal, warn

addToPath("../")

from common import (
    Options,
    Simulation,
    CacheConfig,
    CpuConfig,
    ObjectList,
    MemConfig,
)
from common.FileSystemConfig import config_filesystem
from common.Caches import *

import helper_scripts as hs

print("simpoint_profile")
parser = argparse.ArgumentParser()
args = hs.basic_setup(parser)


num_cpus = 1
print("simpoint_profile")
args.checkpoint_restore = 1
# args.at_instruction = True
args.checkpoint_dir = "cpts"
if not os.path.exists("cpts"):
    print(os.path("cpts"))
    exit()
# args.take_checkpoints = 1400000000
args.simpoint_profile = True
args.simpoint_interval = 100000000
args.cpu_type = "AtomicSimpleCPU"
args.maxinsts = 100000000000

# hs.copy_kernel_checkpoint()

(cpu, mem, futureclass) = Simulation.setCPUClass(args)
TestMemClass = Simulation.setMemClass(args)

cpu.numThreads = 1
print(args)
root, test_sys = hs.build_test_system_fs(args, mem, cpu)
print("Test")
print(args)
print(root)
print(test_sys)
print(futureclass)
Simulation.run(args, root, test_sys, futureclass)
