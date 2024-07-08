import m5
import os
from m5.objects import Root
from gem5.utils.requires import requires
from gem5.components.boards.riscv_board import RiscvBoard
from gem5.components.memory import DualChannelDDR4_2400
from gem5.components.processors.simple_processor import SimpleProcessor
from gem5.components.processors.cpu_types import CPUTypes
from gem5.isas import ISA
from gem5.simulate.simulator import Simulator
from gem5.resources.workload import CustomWorkload
from gem5.resources.resource import CustomResource, CustomDiskImageResource
from gem5.components.cachehierarchies.classic.private_l1_private_l2_cache_hierarchy import PrivateL1PrivateL2CacheHierarchy
from gem5.simulate.exit_event import ExitEvent

requires(isa_required=ISA.RISCV)

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
    function="set_kernel_disk_workload",
    parameters={
        "kernel": CustomResource("/import/lab/users/joseph/.cache/gem5/riscv-bootloader-vmlinux-5.10"),
        "disk_image": CustomDiskImageResource("/import/public/Linux/gem5/RISCV/ubuntu-spec.img")
    }
))

board.workload.dtb_addr = 0x87E00000
board.workload.command_line = "console=ttyS0 root=/dev/vda1 ro"
board._pre_instantiate()


root = Root(full_system=True, system=board)


checkpoint_dir = "/import/lab/users/joseph/Documents/RISCV/gem5-Okapi/configs/cal/neha/checkpoint_dir"  


m5.instantiate(checkpoint_dir)

print("Checkpoint loaded. Continuing simulation...")


simulator = Simulator(board=board)

if m5.curTick() != ExitEvent.EXIT:
    print("Creating benchmark script on the disk image...")

    
    benchmark_script = """
#!/bin/sh

benchmark_base_dir="/root/Spec2006/all/ref"
benchmark_dirs=(
    "400.perlbench" "401.bzip2" "403.gcc" "410.bwaves" "416.gamess"
    "429.mcf" "433.milc" "434.zeusmp" "435.gromacs" "436.cactusADM"
    "437.leslie3d" "444.namd" "445.gobmk" "447.dealII" "450.soplex"
    "453.povray" "454.calculix" "456.hmmer" "458.sjeng" "459.GemsFDTD"
    "462.libquantum" "464.h264ref" "465.tonto" "470.lbm" "471.omnetpp"
    "473.astar" "481.wrf" "482.sphinx3" "483.xalancbmk"
)

iterations=(0 1 2 0 1 2 3 4 5 0 1 2 3 4 5 6 7 8 0 0 0 0 0 0 0 1 2 3 4 0 0 0 1 0 0 0 0 1 2 0 0 0 0 1 0 0 0)

log_file="/root/benchmark_log.txt"
echo "Starting benchmarks..." | tee $log_file

for i in "${!benchmark_dirs[@]}"; do
    benchmark="${benchmark_dirs[$i]}"
    iteration="${iterations[$i]}"

    for j in $(seq 0 "$iteration"); do
        cd "${benchmark_base_dir}/${benchmark}"
        echo "Running ${benchmark}/run_workload${j}.sh" | tee -a $log_file
        /sbin/m5 dumpstats
        /sbin/m5 resetstats
        sh "run_workload${j}.sh"
        if [ $? -eq 0 ]; then
            echo "Completed ${benchmark}/run_workload${j}.sh" | tee -a $log_file
        else
            echo "Failed ${benchmark}/run_workload${j}.sh" | tee -a $log_file
        fi
        /sbin/m5 exit
    done
done
echo "All benchmarks completed." | tee -a $log_file
"""
    benchmark_script_path_host = "/tmp/run_benchmarks.sh"
    with open(benchmark_script_path_host, "w") as f:
        f.write(benchmark_script)
    
    
    os.system(f"m5 cp {benchmark_script_path_host} /root/run_benchmarks.sh")

    print("Benchmark script copied to the simulated environment.")

    
    os.system("m5 shell 'chmod +x /root/run_benchmarks.sh'")

    print("Benchmark script made executable in the simulated environment.")

print("Simulation completed.")
