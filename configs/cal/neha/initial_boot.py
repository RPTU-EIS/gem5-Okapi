import m5
from m5.objects import Root

from gem5.utils.requires import requires
from gem5.components.boards.riscv_board import RiscvBoard
from gem5.components.memory import DualChannelDDR4_2400
from gem5.components.processors.simple_processor import SimpleProcessor
from gem5.components.processors.cpu_types import CPUTypes
from gem5.isas import ISA
from gem5.simulate.simulator import Simulator
from gem5.resources.workload import Workload

from gem5.resources.workload import CustomWorkload
from gem5.resources.resource import AbstractResource
from gem5.resources.resource import CustomResource, CustomDiskImageResource, DiskImageResource


requires(isa_required=ISA.RISCV)

from gem5.components.cachehierarchies.classic.private_l1_private_l2_cache_hierarchy import (
    PrivateL1PrivateL2CacheHierarchy,
)


cache_hierarchy = PrivateL1PrivateL2CacheHierarchy(
    l1d_size="16kB", l1i_size="16kB", l2_size="256kB"
)



memory = DualChannelDDR4_2400(size="3GB")


processor = SimpleProcessor(
    cpu_type=CPUTypes.TIMING, isa=ISA.RISCV, num_cores=1
)


board = RiscvBoard(
    clk_freq="3GHz",
    processor=processor,
    memory=memory,
    cache_hierarchy=cache_hierarchy,
)



board.set_workload(CustomWorkload(
    function = "set_kernel_disk_workload",
    parameters = {
        "kernel" : CustomResource("/import/lab/users/joseph/.cache/gem5/riscv-bootloader-vmlinux-5.10"),
        "disk_image" : CustomDiskImageResource("/import/public/Linux/gem5/RISCV/ubuntu-spec.img") 
    }
))
board.workload.dtb_addr = 0x87E00000
board.workload.command_line = "console=ttyS0 root=/dev/vda1 ro"

simulator = Simulator(board=board)


print("Starting the simulation...")
simulator.run()
print("System booted..")
input("Press Enter to create a checkpoint..")

checkpoint_dir = "/import/lab/users/joseph/Documents/RISCV/gem5-Okapi/configs/cal/neha/checkpoint_dir" 
print("Creating checkpoint...")
m5.checkpoint("/import/lab/users/joseph/Documents/RISCV/gem5-Okapi/configs/cal/neha/checkpoint_dir")
print(f"Checkpoint created at {checkpoint_dir}")
