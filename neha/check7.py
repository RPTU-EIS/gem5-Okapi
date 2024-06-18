import os
import argparse
import m5
from m5.objects import *
from gem5.utils.requires import requires
from gem5.components.boards.riscv_board import RiscvBoard
from gem5.components.memory import SingleChannelDDR3_1600
from gem5.components.cachehierarchies.classic.private_l1_private_l2_cache_hierarchy import PrivateL1PrivateL2CacheHierarchy
from gem5.components.processors.cpu_types import CPUTypes
from gem5.components.processors.simple_processor import SimpleProcessor
from gem5.resources.resource import obtain_resource, DiskImageResource, BootloaderResource, KernelResource
from gem5.isas import ISA

requires(isa_required=ISA.RISCV)

parser = argparse.ArgumentParser(description="Run RISC-V full system simulation with gem5")
parser.add_argument("--bootloader", required=True, help="Path to the bootloader")
parser.add_argument("--kernel", required=True, help="Path to the kernel")
parser.add_argument("--disk_image", required=True, help="Path to the disk image (ubuntu-spec.img)")
parser.add_argument("--benchmark", required=True, help="Name of the benchmark folder in Ubuntu")
parser.add_argument("--workload", type=int, required=True, help="Workload number to run")

args = parser.parse_args()

assert os.path.exists(args.bootloader), f"Bootloader not found at {args.bootloader}"
assert os.path.exists(args.kernel), f"Kernel image not found at {args.kernel}"
assert os.path.exists(args.disk_image), f"Disk image not found at {args.disk_image}"


gem5_init_script = f"""
#!/bin/bash
echo "gem5_init.sh: Starting initialization"

mount -t proc none /proc
mount -t sysfs none /sys
mount -t devtmpfs none /dev


cd /root/{args.benchmark}


/sbin/m5 dumpstats
/sbin/m5 resetstats


sh run_workload{args.workload}.sh


echo "Done :D"
/sbin/m5 exit
"""

clk_freq = '1GHz'

memory = SingleChannelDDR3_1600(size="16GB")

cache_hierarchy = PrivateL1PrivateL2CacheHierarchy(
    l1d_size="32KiB", l1i_size="32KiB", l2_size="512KiB"
)

processor = SimpleProcessor(
    cpu_type=CPUTypes.TIMING, isa=ISA.RISCV, num_cores=1
)

system = RiscvBoard(
    clk_freq=clk_freq,
    processor=processor,
    memory=memory,
    cache_hierarchy=cache_hierarchy
)

system.set_kernel_disk_workload(
    bootloader=BootloaderResource(args.bootloader),
    kernel=KernelResource(args.kernel),
    disk_image=DiskImageResource(args.disk_image),
    readfile_contents=gem5_init_script
)


system.workload.command_line = "console=ttyS0 root=/dev/vda1 rw init=/sbin/init"

print("Pre-instantiating the system...")
system._pre_instantiate()

print("Instantiating the system...")
root = Root(full_system=True, system=system)
m5.instantiate()

print("Beginning simulation!")
exit_event = m5.simulate()

print('Exiting @ tick {} because {}'.format(m5.curTick(), exit_event.getCause()))
