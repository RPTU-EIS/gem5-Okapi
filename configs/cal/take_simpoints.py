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

warmup_length = "50000000"
interval_length = "100000000"

parser = argparse.ArgumentParser()
args = hs.basic_setup(parser)

num_cpus = 1

args.checkpoint_dir = "cpts"
print(args.checkpoint_dir)
args.checkpoint_restore = 1
args.at_instruction = True
args.take_simpoint_checkpoints = (
    f"simpoints/simpoints,"
    f"simpoints/weights,{interval_length},{warmup_length}"
)
args.cpu_type = "AtomicSimpleCPU"
args.maxinsts = 100000000000

(cpu, mem, futureclass) = Simulation.setCPUClass(args)
TestMemClass = Simulation.setMemClass(args)

cpu.numThreads = 1

root, test_sys = hs.build_test_system_fs(args, mem, cpu)
Simulation.run(args, root, test_sys, futureclass)
