import os
import argparse
import shutil
import m5
from m5.objects import *
from gem5.utils.requires import requires
from gem5.components.boards.riscv_board import RiscvBoard
from gem5.components.memory import SingleChannelDDR3_1600
from gem5.components.cachehierarchies.classic.private_l1_private_l2_walk_cache_hierarchy import PrivateL1PrivateL2WalkCacheHierarchy
from gem5.resources.resource import DiskImageResource, KernelResource, CheckpointResource
from gem5.simulate.simulator import Simulator
from gem5.isas import ISA
from gem5.components.processors.cpu_types import CPUTypes
from gem5.components.processors.simple_processor import SimpleProcessor

requires(isa_required=ISA.RISCV)


parser = argparse.ArgumentParser(description="Run RISC-V full system simulation with gem5.")
parser.add_argument("--disk_image", required=True, help="Path to the disk image (e.g., ubuntu-spec.img)")
parser.add_argument("--kernel", required=True, help="Path to the kernel image")
parser.add_argument("--workload", type=int, required=True, help="Workload number to run")
parser.add_argument("--benchmark", required=True, help="Name of the benchmark folder in Ubuntu")
parser.add_argument("--checkpoint_path", required=True, help="Path to the specific checkpoint directory")
parser.add_argument("--speculativeLoadPolicy", required=True, choices=["NaiveDelay", "EagerDelay", "STT"], help="Mitigation scheme")
parser.add_argument("--threatModel", required=True, choices=["Spectre", "Futuristic", "Naive"], help="Threat model")
parser.add_argument("--benchmark_insts", type=int, default=100000000, help="Number of benchmark instructions")
parser.add_argument("--warmup_insts", type=int, default=50000000, help="Number of warmup instructions")


args = parser.parse_args()


if args.speculativeLoadPolicy == "NaiveDelay" and args.threatModel != "Futuristic":
    raise ValueError("NaiveDelay can only be used with the Futuristic threat model.")


print(f"Running simulation with:")
print(f"  Speculative Load Policy: {args.speculativeLoadPolicy}")
print(f"  Threat Model: {args.threatModel}")
checkpoint_name = os.path.basename(args.checkpoint_path)
output_stats_dir = f"/import/lab/users/joseph/Documents/RISCV2/gem5-Okapi/neha/mitigation_stats/STT_Spectre/473.astar/{checkpoint_name}"
os.makedirs(output_stats_dir, exist_ok=True)



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


def apply_mitigations(processor, speculativeLoadPolicy, threatModel):
    """
    Apply speculativeLoadPolicy and threatModel to each core of the processor.
    """
    print(f"Configuring Processor with:")
    print(f"  Speculative Load Policy: {speculativeLoadPolicy}")
    print(f"  Threat Model: {threatModel}")

    for core in processor.get_cores():
        core.core.speculativeLoadPolicy = speculativeLoadPolicy
        core.core.threatModel = threatModel

apply_mitigations(processor, args.speculativeLoadPolicy, args.threatModel)


board = RiscvBoard(
    clk_freq=clk_freq,
    processor=processor,
    memory=memory,
    cache_hierarchy=cache_hierarchy
)

board.set_kernel_disk_workload(
    kernel=KernelResource(args.kernel),
    disk_image=DiskImageResource(args.disk_image, root_partition="1"),
    readfile_contents=gem5_init_script,
    checkpoint=CheckpointResource(args.checkpoint_path)
)


simulator = Simulator(board=board, full_system=True)


def schedule_max_insts(self, inst: int) -> None:
    """
    Schedule a MAX_INSTS exit event when any thread in any core reaches the
    given number of instructions.
    """
    for core in self._board.get_processor().get_cores():
        core._set_inst_stop_any_thread(inst, self._instantiated)


setattr(Simulator, "schedule_max_insts", schedule_max_insts)


print("Starting warmup phase...")
simulator.schedule_max_insts(args.warmup_insts)
simulator.run()
print("Warmup phase completed.")

m5.stats.reset()


simulator.schedule_max_insts(args.benchmark_insts)
simulator.run()
print("Benchmark phase completed.")


m5.stats.dump()  
benchmark_stats_path = os.path.join(output_stats_dir, "benchmark_stats.txt")
shutil.move("/import/lab/users/joseph/Documents/RISCV2/gem5-Okapi/m5out/stats.txt", benchmark_stats_path)
print(f"Benchmark stats dumped to {benchmark_stats_path}")


m5.stats.reset()

print(f"Simulation with {args.speculativeLoadPolicy} and {args.threatModel} completed.")
