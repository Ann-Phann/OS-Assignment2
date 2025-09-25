import sys          # Cross platform Python executable
import os           # Checking the directory
import subprocess   # Running the terminal python script
# import glob         # Finding files
from pathlib import Path
import logging

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M')

# Define constants
TRACE_FOLDER = Path("trace")
REQUIRED_TRACES = {"gcc", "swim", "bzip", "sixpack"} 
RESULTS_FOLDER = Path("output")
MEMSIM_SCRIPT = "simulator.py"  # Assuming it's in the same directory; adjust path if needed
ALGOS = ["rand", "lru", "clock"]
FRAMES = [x for x in range(1,1000 + 1)]  # Your chosen range
MODE = "quiet"

def check():
    """
    Checks if the 'trace/' folder exists. If not, creates it and prompts the user to download traces.
    Returns True if traces are ready (folder exists and has *.trace files), False otherwise.
    """
    try:
        if not TRACE_FOLDER.exists():
            TRACE_FOLDER.mkdir(parents = True, exist_ok = True)
            logging.info(f"Folder '{TRACE_FOLDER}/' does not exist. Creating it now...")
            logging.debug(f"Please download the trace files (gcc.trace, swim.trace, bzip.trace, sixpack.trace) "
                f"and place them in the '{TRACE_FOLDER}/' folder.")
        else:
            logging.info(f"Folder '{TRACE_FOLDER}/' exists. Proceed with checking files...")
            traces = {trace.stem for trace in TRACE_FOLDER.glob("*.trace")}
            found = traces & REQUIRED_TRACES
            missing = REQUIRED_TRACES - traces

            log_list = []
            for item in REQUIRED_TRACES:
                mark = "✓" if item in found else "x"
                if mark == "✓":
                    log_list.append(f"\t\t\t{mark} Found {item}.trace")
                else:
                    log_list.append(f"\t\t\t{mark} Missing {item}.trace")
            
            logging.info("Trace files checklist:\n" + "\n".join(log_list))
            
            ready = (len(missing) == 0)
            if ready:
                logging.info("All traces are found.")
                __run()

            else:
                filenames = {f"{name}.trace" for name in missing}
                msg = f"Please download and put all in '{TRACE_FOLDER}/' as for the missing: {', '.join(filenames)}"
                raise Exception(msg)
    except Exception as e:
        logging.error(e)

def __run():
    """
    Runs the memsim.py for all combinations of traces, algos, and frames.
    Saves output to results/ folder.
    """
    try:
        if not RESULTS_FOLDER.exists():
            RESULTS_FOLDER.mkdir(parents = True, exist_ok = True)
            logging.info(f"Folder '{RESULTS_FOLDER}/' does not exist. Creating it now...")
        
        trace_files = {file for file in TRACE_FOLDER.glob("*.trace")}

        for file in trace_files:
            for algo in ALGOS:
                
                output_file = os.path.join(RESULTS_FOLDER, f"Out_{file.stem}_{algo}_{min(FRAMES)}-{max(FRAMES)}.csv")

                for frame in FRAMES:
                    
                    # Build command
                    command = [
                        sys.executable, MEMSIM_SCRIPT, str(file), str(frame), algo, MODE
                    ]
                    
                    logging.info(f"Running: {' '.join(command)} > {output_file}")

                    # Run the command and redirect output to file
                    proc = subprocess.run(command, stdout = subprocess.PIPE, stderr = subprocess.PIPE, check = True, text = True)
                    contents = ""
                    lines = [line for line in proc.stdout.rstrip().split('\n')]
                    contents = ', '.join(lines)
                    contents = contents + '\n'
                    with open(output_file, "a") as outfile:
                        outfile.write(contents)

                    logging.info(f"Completed simulation. Output is saved at {output_file}")

    except subprocess.CalledProcessError as e:
        logging.error(f"Process failed with exit %d", e.returncode)
        logging.error("stderr:\n\t\t%s", (e.stderr or "<no stderr>").strip())
    
    except FileNotFoundError as e:
        logging.error(f"Missing file(s) occur. Please check all valid files are available or run check(): \n\t\t", e)