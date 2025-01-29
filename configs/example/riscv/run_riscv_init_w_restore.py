import os
import argparse
import m5
from m5.objects import *
from m5.util import addToPath, fatal, warn
from gem5.utils.requires import requires
from gem5.components.boards.riscv_board import RiscvBoard
from gem5.components.memory import SingleChannelDDR3_1600
#from gem5.components.cachehierarchies.classic.no_cache import NoCache
from gem5.simulate.simulator import Simulator
#from gem5.components.cachehierarchies.classic.private_l1_private_l2_cache_hierarchy import PrivateL1PrivateL2CacheHierarchy
from gem5.components.processors.cpu_types import CPUTypes
from gem5.components.processors.simple_processor import SimpleProcessor
from gem5.resources.resource import DiskImageResource, KernelResource, BootloaderResource,CheckpointResource
from gem5.isas import ISA
#addToPath("/import/lab/users/joseph/Documents/RISCV/gem5/configs")
from gem5.components.cachehierarchies.classic.private_l1_private_l2_walk_cache_hierarchy import (
    PrivateL1PrivateL2WalkCacheHierarchy,
)


requires(isa_required=ISA.RISCV)

parser = argparse.ArgumentParser(description="Run RISC-V full system simulation with gem5 and create a checkpoint during boot")
parser.add_argument("--disk_image", required=True, help="Path to the disk image (ubuntu-spec.img)")
parser.add_argument("--kernel", required=True, help="Path to the kernel image")
parser.add_argument("--workload", type=int, required=True, help="Workload number to run")
parser.add_argument("--benchmark", required=True, help="Name of the benchmark folder in Ubuntu")

#Options.addCommonOptions(parser)
#Options.addFSOptions(parser)
args = parser.parse_args()

assert os.path.exists(args.disk_image), f"Disk image not found at {args.disk_image}"
assert os.path.exists(args.kernel), f"Kernel image not found at {args.kernel}"


gem5_init_script = f"""
#!/bin/bash
echo "gem5_init.sh: Starting initialization"



cd /root/Spec2006/all/ref/{args.benchmark}

/sbin/m5 dumpstats
/sbin/m5 resetstats

sh run_workload{args.workload}.sh
echo "Done :D"
/sbin/m5 exit
"""

clk_freq = '3GHz'
memory = SingleChannelDDR3_1600(size="2GB")
cache_hierarchy = PrivateL1PrivateL2WalkCacheHierarchy(l1d_size="32KiB", l1i_size="32KiB", l2_size="512KiB")
#cache_hierarchy = PrivateL1PrivateL2CacheHierarchy(l1d_size="32KiB", l1i_size="32KiB", l2_size="512KiB")
#cache_hierarchy = NoCache()
processor = SimpleProcessor(cpu_type=CPUTypes.ATOMIC, isa=ISA.RISCV, num_cores=1)
board = RiscvBoard(clk_freq=clk_freq, processor=processor, memory=memory, cache_hierarchy=cache_hierarchy)

board.set_kernel_disk_workload( 
    kernel=KernelResource(args.kernel),
    bootloader=BootloaderResource("/import/public/Linux/gem5/RISCV/riscv-bootloader-opensbi-1.3.1"),
    disk_image=DiskImageResource(args.disk_image, root_partition=str(1)),
    checkpoint = CheckpointResource("/import/lab/users/joseph/Documents/RISCV2/gem5-Okapi/m5out/cpt.9084498525216"),
    readfile_contents=gem5_init_script
)

board.workload.command_line = "console=ttyS0 root=/dev/vda1 rw init=/root/gem5_init.sh"

simulator = Simulator(board=board, full_system=True)

print("Starting simulation...")
simulator.run()

