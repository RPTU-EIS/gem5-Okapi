import os
import argparse
import m5
from m5.objects import *
from gem5.utils.requires import requires
from gem5.components.boards.riscv_board import RiscvBoard
from gem5.components.memory import SingleChannelDDR3_1600
from gem5.simulate.simulator import Simulator
from gem5.components.cachehierarchies.classic.private_l1_private_l2_walk_cache_hierarchy import (
    PrivateL1PrivateL2WalkCacheHierarchy,
)
from gem5.components.processors.cpu_types import CPUTypes
from gem5.components.processors.simple_processor import SimpleProcessor
from gem5.resources.resource import DiskImageResource, KernelResource, BootloaderResource, CheckpointResource
from gem5.isas import ISA
from gem5.simulate.exit_event import ExitEvent

requires(isa_required=ISA.RISCV)

parser = argparse.ArgumentParser(description="Restore checkpoint and profile SimPoints in gem5")
parser.add_argument("--disk_image", required=True, help="Path to the disk image (ubuntu-spec.img)")
parser.add_argument("--kernel", required=True, help="Path to the kernel image")
parser.add_argument("--benchmark", required=True, help="Name of the benchmark folder in Ubuntu")
parser.add_argument("--workload", type=int, required=True, help="Workload number to run")
parser.add_argument("--simpoint_interval", type=int, default=100000000, help="SimPoint interval length (default 100 million)")
parser.add_argument("--maxinsts", type=int, default=5000000000, help="Maximum instructions for the simulation (default 5 billion)")
#parser.add_argument("--max_simpoints", type=int, default=5, help="Maximum number of SimPoints (default 5)")
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
processor = SimpleProcessor(cpu_type=CPUTypes.ATOMIC, isa=ISA.RISCV, num_cores=1)
board = RiscvBoard(clk_freq=clk_freq, processor=processor, memory=memory, cache_hierarchy=cache_hierarchy)


board.set_kernel_disk_workload(
    kernel=KernelResource(args.kernel),
    bootloader=BootloaderResource("/import/public/Linux/gem5/RISCV/riscv-bootloader-opensbi-1.3.1"),
    disk_image=DiskImageResource(args.disk_image, root_partition=str(1)),
    checkpoint=CheckpointResource("/import/lab/users/joseph/Documents/RISCV2/gem5-Okapi/neha/checkpoints_after_boot/cpt.9084498525216/"),
    readfile_contents=gem5_init_script
)

board.workload.command_line = "console=ttyS0 root=/dev/vda1 rw init=/root/gem5_init.sh"
simulator = Simulator(board=board, full_system=True)
# Function to schedule SimPoint-based instructions
#def schedule_simpoint_insts(simpoint_start_insts):
 #   if processor.get_cores()[0].get_num_threads() > 1:
  #      raise ValueError("SimPoints only work with one core")
   # processor.get_cores()[0].set_simpoint(simpoint_start_insts, False)


#def schedule_max_insts(inst):
 #   for core in board.get_processor().get_cores():
  #      core._set_inst_stop_any_thread(inst, False)

def schedule_max_insts(self, inst: int) -> None:
    for core in self._board.get_processor().get_cores():
        core._set_inst_stop_any_thread(inst, self._instantiated)

Simulator.schedule_max_insts = schedule_max_insts



simulator.schedule_max_insts(args.maxinsts)


processor.get_cores()[0].core.addSimPointProbe(args.simpoint_interval)





simulator.run()

print("Simulation completed after reaching the instruction limit or simpoints.")
