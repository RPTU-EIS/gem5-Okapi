import argparse
import sys
import os
import shutil

import m5
from gem5.utils.requires import requires
from m5.defines import buildEnv
from m5.objects import *
from m5.params import NULL
from m5.util import addToPath, fatal, warn
from gem5.components.processors.cpu_types import CPUTypes

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


num_cpus = 1

args.at_instruction = True
args.checkpoint_dir = "cpts"
if not os.path.exists("cpts"):
    os.mkdir("cpts")
args.take_checkpoints = 1400000000
print(33)
args.cpu_type = "AtomicSimpleCPU"
print(35)
(cpu, mem, futureclass) = Simulation.setCPUClass(args)
print(37)
TestMemClass = Simulation.setMemClass(args)

cpu.numThreads = 1
root, test_sys = hs.build_test_system_fs(args, mem, cpu)
Simulation.run(args, root, test_sys, futureclass)

# Namespace(STT=None, abs_max_tick=18446744073709551615, arm_iset='arm',
# at_instruction=True, bench=None, benches='spec2017', benchmark=None, bp_type='TournamentBP',
# cacheline_size=64, caches=False, checker=False, checkpoint_at_end=False, checkpoint_dir='cpts',
# checkpoint_restore=None, command_line=None, command_line_file=None, config='blank', cpu_clock='2GHz',
# cpu_type='AtomicSimpleCPU', data_trace_file='', disk_image=['/data/schmitz/AmundKernelAndImage/x86-ubuntu-18.04-img'],
# dist=False, dist_rank=0, dist_server_name='127.0.0.1', dist_server_port=2200, dist_size=0, dist_sync_on_pseudo_op=False,
# dist_sync_repeat='0us', dist_sync_start='5200000000000t', dual=False, elastic_trace_en=False, enable_dram_powerdown=False,
# etherdump=None, ethernet_linkdelay='10us', ethernet_linkspeed='10Gbps', external_memory_system=None, fast_forward=None, frame_capture=False,
# full_system=True, ifPrintROB=None, implicit_channel=None, indirect_bp_type=None, init_param=0, initialize_only=False, inst_trace_file='',
# is_switch=False, iteration=6, kernel='/data/schmitz/AmundKernelAndImage/x86-linux-kernel-5.4.49', l1d_assoc=2, l1d_hwp_type=None, l1d_size='64kB',
# l1i_assoc=2, l1i_hwp_type=None, l1i_size='32kB', l2_assoc=8, l2_hwp_type=None, l2_size='2MB', l2cache=False, l3_assoc=16, l3_size='16MB', list_bp_types=None,
# list_cpu_types=None, list_hwp_types=None, list_indirect_bp_types=None, list_mem_types=None, list_rp_types=None, max_checkpoints=5, maxinsts=None,
# maxtime=None, mem_channels=1, mem_channels_intlv=0, mem_ranks=None, mem_size='512MB', mem_type='DDR3_1600_8x8', memchecker=False, moreTransmitInsts=None,
# needsTSO=None, num_cpus=1, num_dirs=1, num_l2caches=1, num_l3caches=1, num_work_ids=None, os_type='linux', override_vendor_string=None, param=[],
# prog_interval=None, rel_max_tick=None, repeat_switch=None, restore_simpoint_checkpoint=False, restore_with_cpu='AtomicSimpleCPU', root_device=None,
# ruby=False, script='/import/home/schmitz/gem5-private-HW-domain/configs/cal/run_scripts/spec2017/bwaves_s_0.rcS', simpoint=False,
# simpoint_interval=10000000, simpoint_profile=False, smt=False, spec_input='ref', standard_switch=None, stats_root=[], sys_clock='1GHz',
# sys_voltage='1.0V', take_checkpoints=1400000000, take_simpoint_checkpoints=None, threat_model='Futuristic', timesync=False, tlm_memory=None,
# wait_gdb=False, warmup_insts=None, work_begin_checkpoint_count=None, work_begin_cpu_id_exit=None, work_begin_exit_count=None, work_cpus_checkpoint_count=None,
# work_end_checkpoint_count=None, work_end_exit_count=None, work_item_id=None)
