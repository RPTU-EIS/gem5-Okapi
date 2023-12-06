from multiprocessing import Process
import os
import time
import glob
import shutil
import sys
from datetime import datetime

work_root = os.getcwd()
gem5_root = f"/data/schmitz/gem5-Okapi"
gem5 = f"{gem5_root}/build/X86/gem5.opt"
cal = f"{gem5_root}/configs/cal"
results = f"{gem5_root}/results"
checkpoints = f"{gem5_root}/configs/cal/checkpoints"
simfiles = f"{gem5_root}/configs/cal/analysis"
simpoints = f"/data/schmitz/simpoints"

syscall_mode = False
if syscall_mode:
    simfiles = f"{gem5_root}/runs/simpoints"
    simpoints = f"{gem5_root}/runs/simpoints/checkpoints"

sim_tak = f"{cal}/take_simpoints.py"
sim_pro = f"{cal}/simpoint_profile.py"
run_sim = f"{cal}/run_simpoints.py"


def get_names(bench, index):
    if bench == "spec2006":
        with open(f"{cal}/commands/fullnames_06.txt") as names, open(
            f"{cal}/commands/iterations_06.txt"
        ) as it:
            all_names = names.readlines()
            fullname = all_names[index].strip()
            bname = all_names[index].split(".")[1].strip()
            iteration = it.readlines()[index].strip()
            return (fullname, bname, iteration)

    if bench == "spec2017":
        with open(f"{cal}/commands/fullnames_17.txt") as names, open(
            f"{cal}/commands/iterations_17.txt"
        ) as it:
            all_names = names.readlines()
            fullname = all_names[index].strip()
            bname = all_names[index].split(".")[1].strip()
            iteration = it.readlines()[index].strip()
            print(fullname)
            return (fullname, bname, iteration)

    assert False


def get_commands(bench, index):
    if bench == "spec2006":
        with open(f"{cal}/commands/commands_s06.txt") as commands:
            command = commands.readlines()[index].split(" ", 1)[1][:-1]
            return command

    if bench == "spec2017":
        with open(f"{cal}/commands/commands_s17.txt") as commands:
            command = commands.readlines()[index].split(" ", 1)[1][:-1]
            return command

    assert False


def get_extra_args(bench, index, full_system):
    return (
        f"--benches {bench} --iteration {index} "
        f"{'--full-system' if full_system else ''}"
    )


def get_scheme_args(scheme, ap, threat):
    # if ap:
    #    return f" --scheme {scheme} --address_prediction"
    return f" --speculativeLoadPolicy {scheme} --threatModel {threat} --okapiVariation {ap}"


def get_tdiff_scheme_args(scheme, ap):
    assert scheme != 0
    # if not ap:
    #    return f" --scheme '0|{scheme}'"
    return f" --speculativeLoadPolicy {scheme}"  # '|--address_prediction'"


def get_syscall_args(bench, bname, iteration, index):
    with open(f"{gem5_root}/dom/x86-spec-static-ref/commands_s06.txt") as coms:
        lines = coms.read().split("\n")
        line = lines[index]
        print("command is ", line)
        com = line.split(" ", 1)
        return f' -c {com[0][2:]} -o="{com[1]}"'


def copy_results(bname, iteration, wdir, tdir):
    name = f"{bname}_{iteration}"
    src = f"{wdir}/{name}/m5out/stats.txt"
    dst = f"{tdir}/{name}.txt"
    print(src)
    shutil.copy(src, dst)

    src = f"{wdir}/{name}/m5out/simout"
    dst = f"{tdir}/{name}.simout"
    shutil.copy(src, dst)


def sim_copy_results(bench, bname, iteration, wdir, tdir):
    num_sims = get_num_points(bench, bname, iteration)
    name = f"{bname}_{iteration}"
    for x in range(num_sims):
        src = f"{wdir}/{name}/{name}_{x}_out/stats.txt"
        dst = f"{tdir}/{name}_{x}.txt"
        shutil.copy(src, dst)

        src = f"{wdir}/{name}/{name}_{x}_out/simout"
        dst = f"{tdir}/{name}_{x}.simout"
        shutil.copy(src, dst)


def setup_results(rdir, tdir):
    if not os.path.exists(rdir):
        os.mkdir(rdir)
    if os.path.exists(tdir):
        shutil.rmtree(tdir)
    os.mkdir(tdir)


def copy_cpt(bench, bname, iteration):
    cwd = os.getcwd()
    if not os.path.exists("cpts"):
        os.mkdir("cpts")
    src = f"{checkpoints}/{bench}/{bname}_{iteration}-cpt"
    dst = f"{cwd}/cpts/cpt.None.1"
    shutil.copytree(src, dst)
    dst = f"{cwd}/cpts/cpt.1"
    shutil.copytree(src, dst)


def copy_cpt_dir(bench, bname, iteration, wdir):
    if not os.path.exists(f"{wdir}/{bname}_{iteration}/cpts"):
        os.mkdir(f"{wdir}/{bname}_{iteration}/cpts")
    src = f"{checkpoints}/{bench}/{bname}_{iteration}-cpt"
    dst = f"{wdir}/{bname}_{iteration}/cpts/cpt.None.1"
    shutil.copytree(src, dst)
    dst = f"{wdir}/{bname}_{iteration}/cpts/cpt.1"
    shutil.copytree(src, dst)


def cleanup_cpts():
    if os.path.exists("cpts"):
        shutil.rmtree("cpts")
    if os.path.exists("simpoints"):
        shutil.rmtree("simpoints")


def copy_simpoints(bench, bname, iteration):
    cwd = os.getcwd()
    if not os.path.exists("simpoints"):
        os.mkdir("simpoints")
    src = f"{simpoints}/{bench}/{bname}_{iteration}"
    dst = f"{cwd}/simpoints"
    points = os.listdir(src)
    for point in points:
        shutil.copytree(f"{src}/{point}", f"{dst}/{point}")


def copy_simfiles(bench, bname, iteration):
    cwd = os.getcwd()
    if not os.path.exists("simpoints"):
        os.mkdir("simpoints")
    src = f"{simfiles}/{bench}/{bname}_{iteration}"
    dst = f"{cwd}/simpoints"
    shutil.copy(f"{src}.simpoints", f"{dst}/simpoints")
    shutil.copy(f"{src}.weights", f"{dst}/weights")


def copy_binaries(bench, bname, iteration):
    bin_path = f"{gem5_root}/dom/x86-spec-static-ref"
    print(os.listdir(bin_path))
    print(bench)
    binary = next(x for x in os.listdir(bin_path) if bname in x)
    bins = f"{bin_path}/{binary}"
    files = os.listdir(bins)
    for x in files:
        src = f"{bins}/{x}"
        if os.path.isfile(src):
            dst = os.getcwd()
            shutil.copy(src, dst)
        else:
            dst = f"{os.getcwd()}/{x}"
            shutil.copytree(src, dst)


def setup_workdir(wdir):
    if os.path.exists(wdir):
        return
    os.mkdir(wdir)


def setup_rundir(bname, iteration, wdir, scheme, threat, ap):
    tgt = f"{wdir}/{bname}_{iteration}_{scheme}_{threat}_{ap}"
    if os.path.exists(tgt):
        shutil.rmtree(tgt)
    os.mkdir(tgt)


def get_num_points(bench, bname, iteration):
    return len(os.listdir(f"{cal}/simpoints/{bench}/{bname}_{iteration}"))


def run_benchmark(bench, bname, iteration, index, config, scheme, ap):
    args = get_extra_args(bench, index, True)
    # args += get_scheme_args(scheme, ap)

    run_ref = f"{gem5} -r --debug-flags=SyscallAll {cal}/{config} {args}"
    print(run_ref)
    print(f"Finished with code {os.system(run_ref)}")


def run_benchmark_dir(
    bench, bname, iteration, index, config, scheme, ap, wdir
):
    args = get_extra_args(bench, index, True)
    # args += get_scheme_args(scheme, ap)
    args += f" --checkpoint-dir={simpoints}/{bench}/{bname}_{iteration}"

    run_ref = f"{gem5} -r --debug-flags=SyscallAll {cal}/{config} {args}"
    print(run_ref)
    os.chdir(f"{wdir}")
    print(f"Finished with code {os.system(run_ref)}")


def run_tdiff_benchmark(bench, bname, iteration, index, scheme, ap):
    num_sims = get_num_points(bench, bname, iteration)
    args = get_extra_args(bench, index, True)

    # args += get_tdiff_scheme_args(scheme, ap)
    args += f" --checkpoint-dir={simpoints}/{bench}/{bname}_{iteration}"

    for x in range(num_sims):
        redirect = f"-r --outdir={bname}_{iteration}_{x}_out"
        run_ref = (
            f"{gem5_root}/util/tracediff "
            f"{gem5} --debug-flags=Exec,FmtTicksOff "
            f"{run_sim} {args} --sim_num {x}"
        )
        print(run_ref)
        print(f"Finished with code {os.system(run_ref)}")


def run_sim_benchmark(
    bench, bname, iteration, index, scheme, ap, threat, s_name=""
):
    num_sims = get_num_points(bench, bname, iteration)
    args = get_extra_args(bench, index, not syscall_mode)
    args += get_scheme_args(scheme, ap, threat)
    args += f" --checkpoint-dir={simpoints}/{bench}/{bname}_{iteration}"
    if syscall_mode:
        args += get_syscall_args(bench, bname, iteration, index)

    if s_name != "":
        args += f" --config {s_name}"

    for x in range(num_sims):
        # redirect = f"--debug-flags=O3CPUAll,TLB,PageTableWalker"# -r --outdir={bname}_{iteration}_{x}_out_dbg"# --debug-start=6358920803567"#
        # redirect = f"--debug-flags=O3PipeView -r --outdir={bname}_{iteration}_{x}_{scheme}_dbg_out"
        redirect = (
            f"-r --outdir={bname}_{iteration}_{x}_{scheme}_{threat}_{ap}_out"
        )
        run_ref = f"{gem5} {redirect} {run_sim} {args} --sim_num {x}"  # |rotatelogs -t /data/schmitz/gem5_okapi_bench_runs/okapilogperl{x}.log  3G"
        print(run_ref)
        print(f"Finished with code {os.system(run_ref)}")


def get_scheme_and_ap_from_tag(tag):
    if tag == "bl":
        return ("None", "v1")
    if tag == "NaiveDelay":
        return ("NaiveDelay", "v1")
    if tag == "EagerDelay":
        return ("EagerDelay", "v1")
    if tag == "mp" or tag == "delay":
        return (1, "v1")
    if tag == "ap" or tag == "delay+ap" or tag == "mp+ap":
        return (1, "v1")
    if tag == "STT":
        return ("STT", "v1")
    if tag == "stt":
        return (2, "v1")
    if tag == "sap" or tag == "stt+ap":
        return (2, "v1")
    if tag == "dom":
        return (3, "v1")
    if tag == "dap" or tag == "dom+ap":
        return (3, "v1")
    if tag == "Okapiv1":
        return ("Okapi", "v1")
    if tag == "Okapiv2":
        return ("Okapi", "v2")
    assert False


def main():
    print(sys.argv)
    bench = sys.argv[1]
    task = sys.argv[2]

    smp_p, smp_t, smp_r, cpt_t, tdiff, cpt_and_smp_p = [
        False,
        False,
        False,
        False,
        False,
        False,
    ]

    if task == "profile":
        smp_p = True
    elif task == "cptandprofile":
        cpt_and_smp_p = True
    elif task == "take":
        smp_t = True
    elif task == "run":
        smp_r = True
    elif task == "cpt":
        cpt_t = True
    elif task == "tdiff":
        tdiff = True
    else:
        print("Must provide valid task")
        exit(1)

    index = int(sys.argv[3])

    name = sys.argv[4]
    tag = sys.argv[5]

    s_name = sys.argv[6]

    threat = sys.argv[7]

    single = False
    if len(sys.argv) == 9:
        single = True

    special = s_name != "blank"

    scheme, ap = get_scheme_and_ap_from_tag(tag)

    (fullname, bname, iteration) = get_names(bench, index)

    rdir = f"{gem5_root}/results/{bench}"
    tdir = f"{rdir}/{tag}"
    wdir = f"/data/schmitz/gem5_okapi_bench_runs/jobs/{name if not special else f'{name}_{s_name}'}"

    # if index == 0 or single:
    #    if smp_r:
    #        setup_results(rdir, tdir)
    #    setup_workdir(wdir)

    setup_rundir(bname, iteration, wdir, scheme, threat, ap)

    print(smp_p, smp_t, smp_r, cpt_t, tdiff)
    assert sum([smp_p, smp_t, smp_r, cpt_t, tdiff, cpt_and_smp_p]) == 1

    config = ""
    if smp_p:
        config = "simpoint_profile.py"
    elif smp_t:
        config = "take_simpoints.py"
    elif smp_r:
        config = "run_simpoints.py"
    elif cpt_t:
        config = "take_checkpoint.py"
    elif tdiff:
        config = "tracediff_simpoints.py"

    cwd = os.getcwd()

    os.chdir(f"{wdir}/{bname}_{iteration}_{scheme}_{threat}_{ap}")

    if smp_p or smp_t:
        copy_cpt(bench, bname, iteration)

    if smp_t:
        copy_simfiles(bench, bname, iteration)

    if smp_r or tdiff:
        copy_simpoints(bench, bname, iteration)

    if syscall_mode:
        assert bench == "spec2006"
        copy_binaries(bench, bname, iteration)

    # simpoints and tdiff require multiple runs handled by external script
    if smp_r:
        run_sim_benchmark(
            bench, bname, iteration, index, scheme, ap, threat, s_name
        )
    elif tdiff:
        run_tdiff_benchmark(bench, bname, iteration, index, scheme, ap)
    # rest require only a single config-handled run
    elif cpt_and_smp_p:
        # step 1: take checkpoint
        config = "take_checkpoint.py"

        t = datetime.now()
        date_time_string = t.strftime("%Y%m%d%H%M%S")
        run_benchmark(bench, bname, iteration, index, config, scheme, ap)
        # TODO check for exit code
        # step2: copy checkpoint to the file system
        src = f"{wdir}/{bname}_{iteration}/cpts/cpt.None.1400000000"
        dst = f"{checkpoints}/{bench}/{bname}_{iteration}-cpt"
        step_2_successfull = False

        if os.path.exists(src):
            shutil.copytree(src, dst)
            step_2_successfull = True
        else:
            print(
                "No checkpoint created during cpt take step. Skipping profile step!"
            )
        # additionally copy the working dir into the backup folder to be able to check it later
        src = f"{wdir}"
        dst = f"/data/schmitz/gem5_okapi_bench_runs/python_backup/{bname}_{iteration}_cpt_{date_time_string}"
        shutil.copytree(src, dst)
        # step3 prepare the jobs directory to be able to run the profile step

        # step3 profile the checkpoint
        if step_2_successfull:
            setup_rundir(bname, iteration, wdir, scheme)
            copy_cpt_dir(bench, bname, iteration, wdir)
            config = "simpoint_profile.py"
            bmark_dir = f"{wdir}/{bname}_{iteration}"
            run_benchmark_dir(
                bench, bname, iteration, index, config, scheme, ap, bmark_dir
            )
    elif smp_t:
        run_benchmark(bench, bname, iteration, index, config, scheme, ap)
        # src = f"{wdir}/{bname}_{iteration}/m5out/cpt.simpoint*"
        dst_base = f"/import/home/share_folder/Simpoint_checkpoints/{bname}"
        for src in glob.glob(
            f"{wdir}/{bname}_{iteration}/m5out/cpt.simpoint*"
        ):
            simpoint = src.split("/")[-1]
            dst = f"{dst_base}/{bname}_{iteration}/{simpoint}"
            print(dst)
            shutil.copytree(src, dst)

    else:
        run_benchmark(bench, bname, iteration, index, config, scheme, ap)

    if smp_r or tdiff:
        cleanup_cpts()
    os.chdir(cwd)

    if smp_r:
        sim_copy_results(bench, bname, iteration, wdir, tdir)
    # Don't need results from other runs
    # else:
    #    copy_results(bname, iteration, wdir, tdir)


main()
