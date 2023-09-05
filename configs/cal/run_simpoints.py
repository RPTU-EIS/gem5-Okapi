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


parser = argparse.ArgumentParser()
args = hs.basic_setup(parser)

print("Entering run simpoints config " "with args.sim =", args.full_system)

args.restore_simpoint_checkpoint = True
# args.checkpoint_dir = "/import/home/schmitz/gem5-private-HW-domain/configs/cal/simpoints/spec2017/mcf_s_0/"
# assert os.path.exists(
#    "/import/home/schmitz/gem5-private-HW-domain/configs/cal/simpoints/spec2017/mcf_s_0/"
# )
# args.cpu_type = "TimingSimpleCPU"
args.checkpoint_restore = args.sim_num + 1
args.maxinsts = 100000000

num_cpus = 1

(cpu, mem, futureclass) = Simulation.setCPUClass(args)
TestMemClass = Simulation.setMemClass(args)

cpu.numThreads = 1
futureclass.speculativeLoadPolicy = args.speculativeLoadPolicy
futureclass.threatModel = args.threatModel
print("cpu")
print(cpu)
if args.full_system:
    root, test_sys = hs.build_test_system_fs(args, mem, cpu)
else:
    root, test_sys = hs.build_test_system_se(args, mem, cpu)

Simulation.run(args, root, test_sys, futureclass)
