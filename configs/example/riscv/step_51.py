import os
import argparse
import m5
from m5.objects import *
from gem5.utils.requires import requires
from gem5.components.boards.riscv_board import RiscvBoard
from gem5.components.memory import SingleChannelDDR3_1600
from gem5.components.cachehierarchies.classic.private_l1_private_l2_walk_cache_hierarchy import PrivateL1PrivateL2WalkCacheHierarchy
from gem5.components.processors.cpu_types import CPUTypes
from gem5.components.processors.simple_processor import SimpleProcessor
from gem5.resources.resource import DiskImageResource, KernelResource, BootloaderResource, CheckpointResource
from gem5.isas import ISA
from gem5.simulate.simulator import Simulator



requires(isa_required=ISA.RISCV)


parser = argparse.ArgumentParser(description="Run RISC-V full system simulation with gem5.")
parser.add_argument("--disk_image", required=True, help="Path to the disk image (e.g., ubuntu-spec.img)")
parser.add_argument("--kernel", required=True, help="Path to the kernel image")
parser.add_argument("--workload", type=int, required=True, help="Workload number to run")
parser.add_argument("--benchmark", required=True, help="Name of the benchmark folder in Ubuntu")
parser.add_argument("--benchmark_insts", type=int, default=1000000, help="Number of benchmark instructions")
parser.add_argument("--warmup_insts", type=int, default=500000, help="Number of warmup instructions")
parser.add_argument("--checkpoint_path", required=True, help="Path to the specific checkpoint directory")


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


processor = SimpleProcessor(
    cpu_type=CPUTypes.O3,
    isa=ISA.RISCV,
    num_cores=1
)



board = RiscvBoard(
    clk_freq=clk_freq,
    processor=processor,
    memory=memory,
    cache_hierarchy=cache_hierarchy
)


board.set_kernel_disk_workload(
    kernel=KernelResource(args.kernel),
    bootloader=BootloaderResource("/import/public/Linux/gem5/RISCV/riscv-bootloader-opensbi-1.3.1"),
    disk_image=DiskImageResource(args.disk_image, root_partition=str(1)),
    checkpoint=CheckpointResource(args.checkpoint_path),
    readfile_contents=gem5_init_script
)




simulator = Simulator(board=board, full_system=True)



def schedule_max_insts(self, inst: int) -> None:
    """
    Schedule a MAX_INSTS exit event when any thread in any core reaches the
    given number of instructions.
    :param inst: A number of instructions to run to.
    """
    for core in self._board.get_processor().get_cores():
        core._set_inst_stop_any_thread(inst, self._instantiated)

def get_last_exit_event_cause(self) -> str:
    """
    Returns the last exit event cause.
    """
    if self._last_exit_event:
        return self._last_exit_event.getCause()
    return "No exit event recorded."


Simulator.schedule_max_insts = schedule_max_insts
Simulator.get_last_exit_event_cause = get_last_exit_event_cause



simulator.schedule_max_insts(args.warmup_insts)
simulator.run()

print("Warmup phase completed.")

#exit_cause = simulator.get_last_exit_event_cause()
#print(f"Exit cause after warmup phase: {exit_cause}")

    
m5.stats.reset()
print("Statistics reset after warmup.")

     
simulator.schedule_max_insts(args.benchmark_insts)
simulator.run()
#exit_cause = simulator.get_last_exit_event_cause()
#print(f"Exit cause after benchmark phase: {exit_cause}")

    
m5.stats.dump()
print("Benchmark phase completed.")
m5.stats.reset()
