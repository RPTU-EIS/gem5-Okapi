import os
import argparse
import subprocess


parser = argparse.ArgumentParser(description="Run the checkpoint script on all checkpoints.")
parser.add_argument("--checkpoints_dir", required=True, help="Path to the directory containing all checkpoints.")
parser.add_argument("--disk_image", required=True, help="Path to the disk image")
parser.add_argument("--kernel", required=True, help="Path to the kernel image")
parser.add_argument("--workload", type=int, required=True, help="Workload number to run")
parser.add_argument("--benchmark", required=True, help="Name of the benchmark folder in Ubuntu")
parser.add_argument("--benchmark_insts", type=int, default=100000000, help="Number of benchmark instructions")
parser.add_argument("--warmup_insts", type=int, default=50000000, help="Number of warmup instructions")
parser.add_argument("--speculativeLoadPolicy", required=True, choices=["NaiveDelay", "EagerDelay", "STT", "Okapi"], help="Mitigation scheme")
parser.add_argument("--threatModel", required=True, choices=["Spectre", "Futuristic", "Naive"], help="Threat model")
args = parser.parse_args()


checkpoints = [d for d in os.listdir(args.checkpoints_dir) if os.path.isdir(os.path.join(args.checkpoints_dir, d))]

for checkpoint in checkpoints:
    checkpoint_path = os.path.join(args.checkpoints_dir, checkpoint)
    print(f"Running for checkpoint: {checkpoint_path}")
    
   
    subprocess.run([
        "/import/lab/users/joseph/Documents/RISCV2/gem5-Okapi/build/RISCV/gem5.opt", "/import/lab/users/joseph/Documents/RISCV2/gem5-Okapi/configs/example/riscv/step_5mit.py",
        "--disk_image", args.disk_image,
        "--kernel", args.kernel,
        "--workload", str(args.workload),
        "--benchmark", args.benchmark,
        "--benchmark_insts", str(args.benchmark_insts),
        "--warmup_insts", str(args.warmup_insts),
        "--checkpoint_path", checkpoint_path,
        "--speculativeLoadPolicy", args.speculativeLoadPolicy,
        "--threatModel",args.threatModel
    ])
    
    print(f"Completed checkpoint: {checkpoint_path}")
