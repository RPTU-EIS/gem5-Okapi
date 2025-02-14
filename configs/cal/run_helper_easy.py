from multiprocessing import Process
import os
import time
import glob
import shutil
import sys
from pathlib import Path

work_root = os.getcwd()
gem5_root = f"/data/schmitz/gem5-Okapi"
gem5 = f"{gem5_root}/build/X86/gem5.opt"
cal = f"{gem5_root}/configs/cal"
results = f"{gem5_root}/results"
checkpoints = f"{gem5_root}/configs/cal/checkpoints"
simfiles = f"{gem5_root}/configs/cal/analysis"
simpoints = f"/data/schmitz/simpoints"

run_sim = f"{cal}/run_simpoints.py"


def get_names(bench, index):

    with open(f"{cal}/commands/fullnames_17.txt") as names, open(
        f"{cal}/commands/iterations_17.txt"
    ) as it:
        all_names = names.readlines()
        fullname = all_names[index].strip()
        bname = all_names[index].split(".")[1].strip()
        iteration = it.readlines()[index].strip()
        print(fullname)
        print(bname)
        print(iteration)
        return (fullname, bname, iteration)


def get_extra_args(bench, index, full_system):
    return (
        f"--benches {bench} --iteration {index} "
        f"{'--full-system' if full_system else ''}"
    )


def get_scheme_args(scheme, ap, threat):
    return f" --speculativeLoadPolicy {scheme} --threatModel {threat} --okapiVariation {ap}"


def setup_results(rdir, tdir):
    if not os.path.exists(rdir):
        os.mkdir(rdir)
    if os.path.exists(tdir):
        shutil.rmtree(tdir)
    os.mkdir(tdir)


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
    return len(os.listdir(f"{simpoints}/{bench}/{bname}_{iteration}"))


def run_sim_benchmark(
    bench, bname, iteration, index, scheme, ap, threat, reset, s_name=""
):
    num_sims = get_num_points(bench, bname, iteration)
    args = get_extra_args(bench, index, True)
    args += get_scheme_args(scheme, ap, threat)
    args += f" --checkpoint-dir={simpoints}/{bench}/{bname}_{iteration}"

    if s_name != "":
        args += f" --config {s_name}"

    for x in range(num_sims):
        redirect = f"--debug-flags=O3CPUAll,TLB,PageTableWalker"  # -r --outdir={bname}_{iteration}_{x}_out_dbg"# --debug-start=6358920803567"#
        # redirect = f"--debug-flags=O3PipeView -r --outdir={bname}_{iteration}_{x}_{scheme}_dbg_out"
        # redirect = (
        #    f"-r --outdir={bname}_{iteration}_{x}_{scheme}_{threat}_{ap}_out"
        # )
        if reset == True:
            run_ref = f"{gem5} {redirect} {run_sim} {args} --sim_num {x} --okapiReset |rotatelogs -t /data/schmitz/gem5_okapi_bench_runs/okapilogperl{x}.log  3G"
        else:
            run_ref = f"{gem5} {redirect} {run_sim} {args} --sim_num {x}"  # --okapiReset"  # |rotatelogs -t /data/schmitz/gem5_okapi_bench_runs/okapilogperl{x}.log  3G"
        print(run_ref)
        print(f"Finished with code {os.system(run_ref)}")


def get_scheme_and_ap_from_tag(tag):
    if tag == "bl":
        return ("None", "v1")
    if tag == "NaiveDelay":
        return ("NaiveDelay", "v1")
    if tag == "EagerDelay":
        return ("EagerDelay", "v1")
    if tag == "STT":
        return ("STT", "v1")
    if tag == "Okapiv2":
        return ("Okapi", "v2")
    assert False


def print_scheme_menu():
    print("Select an option:")
    print("0. Run baseline design")
    print("1. Run Okapi")
    print("2. Run EagerDelay")
    print("3. Run NaiveDelay")
    print("4. Run DIFT")


def get_scheme_from_menu(user_input):
    if user_input == "0":
        return ("None", "v1")
    if user_input == "1":
        return ("Okapi", "v2")
    if user_input == "2":
        return ("EagerDelay", "v1")
    if user_input == "3":
        return ("NaiveDelay", "v1")
    if user_input == "4":
        return ("STT", "v1")


def print_benchmark_menu():
    print("Select a benchmark:")

    with open(f"{cal}/commands/fullnames_17.txt") as file, open(
        f"{cal}/commands/iterations_17.txt"
    ) as it:
        all_names = file.readlines()
        all_its = it.readlines()
        for i in range(len(all_names)):
            print(
                str(i)
                + ":\t"
                + all_names[i].rstrip()
                + "\t"
                + all_its[i].rstrip()
            )


def get_bmark_from_menu(user_input):

    with open(f"{cal}/commands/fullnames_17.txt") as names, open(
        f"{cal}/commands/iterations_17.txt"
    ) as it:

        all_names = names.readlines()
        fullname = all_names[int(user_input)].strip()
        bname = all_names[int(user_input)].split(".")[1].strip()
        iteration = it.readlines()[int(user_input)].strip()

        return (fullname, bname, iteration)


def print_reset_menu():
    print("Select an option:")
    print("0. Enable  okapiReset instruction")
    print("1. Disable okapiReset instruction")


def get_reset_from_menu(user_input):
    if user_input == "0":
        return True
    if user_input == "1":
        return False


# helper function for menu
def get_options():
    print_scheme_menu()
    user_input = input("Enter a number between 0 and 4: ")
    while not (user_input.isdigit() and 0 <= int(user_input) <= 4):
        print("\n\n\nInvalid input. Please enter a digit between 0 and 4!")
        print_scheme_menu()
        user_input = input("Enter your choice: ")

    (scheme, ap) = get_scheme_from_menu(user_input)

    print_benchmark_menu()
    user_input = input("Enter a number between 0 and 27: ")
    while not (user_input.isdigit() and 0 <= int(user_input) <= 27):
        print("\n\n\nInvalid input. Please enter a digit between 0 and 27!")
        print_benchmark_menu()
        user_input = input("Enter your choice: ")

    (fullname, bname, iteration) = get_bmark_from_menu(user_input)
    index = user_input
    threat = "Futuristic"

    print_reset_menu()
    user_input = input("Enter a number between 0 and 1: ")
    while not (user_input.isdigit() and 0 <= int(user_input) <= 1):
        print("\n\n\nInvalid input. Please enter a digit between 0 and 1!")
        print_reset_menu()
        user_input = input("Enter your choice: ")

    (reset) = get_reset_from_menu(user_input)

    return (fullname, bname, iteration, scheme, ap, reset, threat, index)


def main():

    print(sys.argv)
    # reset = sys.argv[10]

    smp_r = True
    bench = "spec2017"

    if len(sys.argv) < 2:
        (
            fullname,
            bname,
            iteration,
            scheme,
            ap,
            reset,
            threat,
            index,
        ) = get_options()
        print("YO")
    else:
        index = int(sys.argv[1])
        name = sys.argv[2]
        tag = sys.argv[3]

        s_name = sys.argv[4]

        threat = sys.argv[5]

        reset_s = ""
        reset = False

        if len(sys.argv) == 7:
            reset_s = sys.argv[6]

        if reset_s == "okapiReset":
            reset = True

        special = s_name != "blank"

        scheme, ap = get_scheme_and_ap_from_tag(tag)

        (fullname, bname, iteration) = get_names(bench, index)

    rdir = f"{gem5_root}/results/{bench}"
    wdir = f"/data/schmitz/gem5_okapi_bench_runs/jobs/{bname}"

    setup_rundir(bname, iteration, wdir, scheme, threat, ap)

    config = "run_simpoints.py"

    cwd = os.getcwd()

    os.chdir(f"{wdir}/{bname}_{iteration}_{scheme}_{threat}_{ap}")

    if smp_r or tdiff:
        copy_simpoints(bench, bname, iteration)

    # simpoints and tdiff require multiple runs handled by external script
    if smp_r:
        run_sim_benchmark(
            bench, bname, iteration, index, scheme, ap, threat, reset, ""
        )

    cleanup_cpts()
    os.chdir(cwd)


main()
