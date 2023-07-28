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

from common.FSConfig import *
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

gem5_root = "/data/schmitz/gem5-Okapi"

disk_image = f"/import/home/schmitz/AmundKernelAndImage/x86-3.img"
kernel = f"/import/home/schmitz/AmundKernelAndImage/plinux"
script_path = f"{gem5_root}/configs/cal/run_scripts"
checkpoints = f"{gem5_root}/configs/cal/checkpoints"


def get_processes(args):
    """Interprets provided args and returns a list of processes"""

    multiprocesses = []
    inputs = []
    outputs = []
    errouts = []
    pargs = []

    workloads = args.cmd.split(";")
    if args.input != "":
        inputs = args.input.split(";")
    if args.output != "":
        outputs = args.output.split(";")
    if args.errout != "":
        errouts = args.errout.split(";")
    if args.options != "":
        pargs = args.options.split(";")

    idx = 0
    for wrkld in workloads:
        process = Process(pid=100 + idx)
        process.executable = wrkld
        process.cwd = os.getcwd()
        process.gid = os.getgid()

        if args.env:
            with open(args.env, "r") as f:
                process.env = [line.rstrip() for line in f]

        if len(pargs) > idx:
            process.cmd = [wrkld] + pargs[idx].split()
        else:
            process.cmd = [wrkld]

        if len(inputs) > idx:
            process.input = inputs[idx]
        if len(outputs) > idx:
            process.output = outputs[idx]
        if len(errouts) > idx:
            process.errout = errouts[idx]

        multiprocesses.append(process)
        idx += 1

    assert not args.smt

    return multiprocesses, 1


def copy_kernel_checkpoint():
    cwd = os.getcwd()
    src = f"{checkpoints}/kernel-cpt"
    dst = f"{cwd}/cpts/cpt.1"
    shutil.copytree(src, dst)


def basic_setup(parser):
    Options.addCommonOptions(parser)
    Options.addCALOptions(parser)

    if "--full-system" in sys.argv:
        Options.addFSOptions(parser)
        Options.addSimpointRunOptions(parser)
    else:
        Options.addSEOptions(parser)

    args = parser.parse_args()
    print(
        "Adding options for ",
        "full system" if args.full_system else "syscall mode",
    )

    args.script = get_script(args.benches, args.iteration)

    args = get_default_args(args)

    if args.full_system:
        args = extend_fs(args)
    else:
        print("Running in legacy system emulation mode")

    if args.config != None and args.config != "blank":
        args = get_advanced_args(args)

    return args


def get_advanced_args(args):
    return extend_with_config(args, f"{args.config}.cfg")


def get_default_args(args):
    return extend_with_config(args, "default_config.cfg")


def extend_fs(args):
    args_d = vars(args)

    xtra = get_fs_args(args.script)
    for x in xtra:
        args_d[x[0]] = x[1]

    args = argparse.Namespace(**args_d)
    return args


def extend_with_config(args, filename):
    args_d = vars(args)

    xtra = read_config(filename)
    for x in xtra:
        args_d[x[0]] = x[1]

    dels = []
    for pair in args_d.items():
        if pair[1] == "Delete":
            dels.append(pair[0])

    for key in dels:
        del args_d[key]

    args = argparse.Namespace(**args_d)
    return args


def get_script(benches, index):
    print(script_path, benches)
    with open(f"{script_path}/{benches}/indexed_list.txt") as scripts:
        scripts = scripts.read()
        scripts = scripts.split("\n")
        print(scripts)
        print(scripts[index])
        # print({script_path}/{benches}/{scripts[index]})
        return f"{script_path}/{benches}/{scripts[index]}"


def read_config(filename):
    args = []
    with open(f"{gem5_root}/configs/cal/configs/{filename}") as config:
        lines = config.read().split("\n")
        for line in lines:
            if len(line) == 0 or line[0] == "#":
                continue
            arg = line.split("=")
            if len(arg) == 1:
                args.append((arg[0].replace("-", "_"), True))
                print(arg[0])
            else:
                args.append((arg[0].replace("-", "_"), arg[1]))
                print(arg[0])
                print(arg[1])
    print(args)
    return args


def get_fs_args(script_name):
    args = []
    args.append(("disk_image", [disk_image]))
    args.append(("kernel", kernel))
    args.append(("script", script_name))
    print(args)
    return args


def build_test_system_fs(args, test_mem_mode, cpu):
    workload = [
        SysConfig(
            disks=args.disk_image,
            rootdev=args.root_device,
            mem=args.mem_size,
            os_type=args.os_type,
        )
    ]

    print(args.mem_size)
    test_sys = makeLinuxX86System(test_mem_mode, 1, workload[0])

    test_sys.cache_line_size = 64

    test_sys.voltage_domain = VoltageDomain(voltage="3.3V")
    test_sys.clk_domain = SrcClockDomain(
        clock="3GHz", voltage_domain=test_sys.voltage_domain
    )

    test_sys.cpu_voltage_domain = VoltageDomain()
    test_sys.cpu_clk_domain = SrcClockDomain(
        clock="3GHz", voltage_domain=test_sys.cpu_voltage_domain
    )

    test_sys.workload.object_file = binary(args.kernel)
    test_sys.readfile = args.script

    test_sys.init_param = args.init_param

    test_sys.cpu = [cpu(clk_domain=test_sys.cpu_clk_domain, cpu_id=0)]

    if args.simpoint_profile:
        test_sys.cpu[0].addSimPointProbe(args.simpoint_interval)

    bpClass = ObjectList.bp_list.get(args.bp_type)
    test_sys.cpu[0].branchPred = bpClass()

    test_sys.iocache = IOCache(addr_ranges=test_sys.mem_ranges)
    test_sys.iocache.cpu_side = test_sys.iobus.mem_side_ports
    test_sys.iocache.mem_side = test_sys.membus.cpu_side_ports

    test_sys.cpu[0].createThreads()

    CacheConfig.config_cache(args, test_sys)
    MemConfig.config_mem(args, test_sys)
    print("yo")
    print(MemConfig)
    root = Root(full_system=True, system=test_sys)
    print(test_sys)
    return (root, test_sys)


def build_test_system_se(args, mem, cpu):
    system = System(
        cpu=[cpu(cpu_id=0)],
        mem_mode=mem,
        mem_ranges=[AddrRange("8GB")],
        cache_line_size="64",
    )

    system.voltage_domain = VoltageDomain(voltage="3.3V")
    system.clk_domain = SrcClockDomain(
        clock="3GHz", voltage_domain=system.voltage_domain
    )

    system.cpu_voltage_domain = VoltageDomain()
    system.cpu_clk_domain = SrcClockDomain(
        clock="3GHz", voltage_domain=system.cpu_voltage_domain
    )

    multiprocesses, numThreads = get_processes(args)

    if args.simpoint_profile:
        system.cpu[0].addSimPointProbe(args.simpoint_interval)

    bpClass = ObjectList.bp_list.get(args.bp_type)
    system.cpu[0].branchPred = bpClass()

    MemClass = Simulation.setMemClass(args)
    system.membus = SystemXBar()
    system.system_port = system.membus.cpu_side_ports
    CacheConfig.config_cache(args, system)
    MemConfig.config_mem(args, system)
    config_filesystem(system, args)

    mp0_path = multiprocesses[0].executable

    system.cpu[0].workload = multiprocesses[0]
    system.cpu[0].createThreads()

    system.workload = SEWorkload.init_compatible(mp0_path)

    root = Root(full_system=False, system=system)
    return (root, system)
