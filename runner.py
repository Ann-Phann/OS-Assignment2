import os           # Checking the directory
import subprocess   # Running the terminal python script
import glob         # Finding files

# Define constants
TRACE_FOLDER = "trace"
RESULTS_FOLDER = "output"
MEMSIM_SCRIPT = "memsim.py"  # Assuming it's in the same directory; adjust path if needed
ALGOS = ["rand", "lru", "clock"]
FRAMES = [1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024, 2048, 4096]  # Your chosen range
MODE = "quiet"

def check_and_prepare_trace_folder():
    """
    Checks if the 'trace/' folder exists. If not, creates it and prompts the user to download traces.
    Returns True if traces are ready (folder exists and has *.trace files), False otherwise.
    """
    if not os.path.exists(TRACE_FOLDER):
        print(f"Folder '{TRACE_FOLDER}/' does not exist. Creating it now...")
        os.makedirs(TRACE_FOLDER)
        print(f"Please download the trace files (gcc.trace, swim.trace, bzip.trace, sixpack.trace) "
              f"and place them in the '{TRACE_FOLDER}/' folder.")
        print("You can decompress them if they are .gz files using 'gunzip -d *.gz' in the folder.")
        input("Press Enter once you've added the files and are ready to proceed...")
        return False  # Force re-check after user input
    else:
        # Check for *.trace files
        trace_files = glob.glob(os.path.join(TRACE_FOLDER, "*.trace"))
        if not trace_files:
            print(f"No *.trace files found in '{TRACE_FOLDER}/'. Please add them now.")
            input("Press Enter once you've added the files and are ready to proceed...")
            return False
        else:
            print(f"Found {len(trace_files)} trace files in '{TRACE_FOLDER}/'. Proceeding...")
            return True

def run_simulations():
    """
    Runs the memsim.py for all combinations of traces, algos, and frames.
    Saves output to results/ folder.
    """
    os.makedirs(RESULTS_FOLDER, exist_ok=True)
    
    trace_files = glob.glob(os.path.join(TRACE_FOLDER, "*.trace"))
    for trace_path in trace_files:
        trace_name = os.path.basename(trace_path).replace(".trace", "")  # e.g., "gcc"
        for algo in ALGOS:
            for frames in FRAMES:
                output_file = os.path.join(RESULTS_FOLDER, f"{trace_name}_{algo}_{frames}.txt")
                
                # Build command
                command = [
                    "python3", MEMSIM_SCRIPT, trace_path, str(frames), algo, MODE
                ]
                
                print(f"Running: {' '.join(command)} > {output_file}")
                
                # Run the command and redirect output to file
                with open(output_file, "w") as outfile:
                    subprocess.run(command, stdout=outfile, stderr=subprocess.PIPE)
                
                print(f"Completed: {output_file}")

if __name__ == "__main__":
    while not check_and_prepare_trace_folder():
        pass  # Loop until traces are ready
    run_simulations()
    print("All simulations completed. Results are in 'results/' folder.")