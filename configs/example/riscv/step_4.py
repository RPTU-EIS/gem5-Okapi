import os
import argparse
import m5
from m5.objects import *
from gem5.utils.requires import requires
from gem5.components.boards.riscv_board import RiscvBoard
from gem5.components.memory import SingleChannelDDR3_1600
from gem5.simulate.simulator import Simulator
from gem5.components.cachehierarchies.classic.private_l1_private_l2_walk_cache_hierarchy import PrivateL1PrivateL2WalkCacheHierarchy
from gem5.components.processors.cpu_types import CPUTypes
from gem5.components.processors.simple_processor import SimpleProcessor
from gem5.resources.resource import DiskImageResource, KernelResource, BootloaderResource, CheckpointResource
from gem5.isas import ISA
import re
from os.path import join as joinpath

requires(isa_required=ISA.RISCV)

parser = argparse.ArgumentParser(description="Restore checkpoint and profile SimPoints in gem5")
parser.add_argument("--disk_image", required=True, help="Path to the disk image (ubuntu-spec.img)")
parser.add_argument("--kernel", required=True, help="Path to the kernel image")
parser.add_argument("--benchmark", required=True, help="Name of the benchmark folder in Ubuntu")
parser.add_argument("--workload", type=int, required=True, help="Workload number to run")
parser.add_argument("--simpoint_file", required=True, help="Path to the SimPoints file")
parser.add_argument("--weights_file", required=True, help="Path to the Weights file")
parser.add_argument("--checkpoint_dir", required=True, help="Directory to save the checkpoint")
parser.add_argument("--warmup_length", type=int, default=50000000, help="Warmup instructions before taking a checkpoint")
parser.add_argument("--interval_length", type=int, default=100000000, help="SimPoint interval length")
parser.add_argument("--simpoint_line_number", type=int, default=0, help="Line number of the SimPoint to target")
args = parser.parse_args()

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
    checkpoint=CheckpointResource("/import/lab/users/joseph/Documents/RISCV2/gem5/m5out/cpt.9084656584332/"),
    readfile_contents=gem5_init_script 
)


def parse_simpoint_at_line(simpoint_filename, weight_filename, interval_length, warmup_length, line_number):
    with open(simpoint_filename, 'r') as sp_file, open(weight_filename, 'r') as wt_file:
        
        for current_line in range(line_number + 1):
            sp_line = sp_file.readline()
            wt_line = wt_file.readline()
            
            
            if not sp_line or not wt_line:
                raise ValueError(f"Line number {line_number} exceeds the number of lines in the SimPoint or weight file.")
        print(f"Read line for SimPoint: '{sp_line.strip()}', Weight: '{wt_line.strip()}'")
       
        sp_match = re.match(r"(\d+)\s+(\d+)", sp_line)
        wt_match = re.match(r"([0-9\.e\-]+)\s+(\d+)", wt_line)
        if not sp_match or not wt_match:
            raise ValueError("Unrecognized line format in SimPoint or weight file!")
        
        interval = int(sp_match.group(1))
        weight = float(wt_match.group(1))

       
        starting_inst_count = max(interval * interval_length - warmup_length, 0)
        actual_warmup_length = warmup_length if starting_inst_count > 0 else interval * interval_length
        
        return (interval, weight, starting_inst_count, actual_warmup_length)

simulator = Simulator(board=board, full_system=True)
#def schedule_max_insts(inst):
  #  """
    #Schedule a MAX_INSTS exit event when the given instruction count is reached
    #on any thread of any core in the processor.
    #"""
    #for core in board.get_processor().get_cores():
      #  core._set_inst_stop_any_thread(inst, False) 

def schedule_max_insts(self, inst: int) -> None:
    for core in self._board.get_processor().get_cores():
        core._set_inst_stop_any_thread(inst, self._instantiated)

Simulator.schedule_max_insts = schedule_max_insts

def takeSingleSimpointCheckpoint(simulator, checkpoint_dir, simpoint):
    interval, weight, starting_inst_count, actual_warmup_length = simpoint

    
    simulator.schedule_max_insts(starting_inst_count)

    
   
    simulator.run()

   
    checkpoint_name = f"cpt.simpoint_inst_{starting_inst_count}_weight_{weight:.8f}"
    m5.checkpoint(joinpath(checkpoint_dir, checkpoint_name))
    print(f"Checkpoint taken at instruction count: {starting_inst_count}, tick: {m5.curTick()}")


#simulator = Simulator(board=board, full_system=True)


simpoint = parse_simpoint_at_line(args.simpoint_file, args.weights_file, args.interval_length, args.warmup_length, args.simpoint_line_number)


takeSingleSimpointCheckpoint(simulator, args.checkpoint_dir, simpoint)
