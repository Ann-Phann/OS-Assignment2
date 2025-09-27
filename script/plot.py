from matplotlib import rc
from pathlib import Path
from itertools import cycle
import matplotlib.pyplot as plt
import numpy as np
import os
import logging

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M')

rc('font', **{'family': 'serif', 'serif': ['Computer Modern']})
rc('text', usetex=True)

OUTPUT_FOLDER = Path("graph")
DATA_FOLDER = Path("output")
TRACE_FOLDER = Path('trace')
FEATURES = {
    'fs': 0,    # Frame size
    'tdr': 2,   # Total disk read
    'tdw': 3,   # Total disk write
    'pfr': -1   # Page fault rate
}
CSV_FILES = DATA_FOLDER.glob('*.csv')
AVAILABLE_GRAPHS = OUTPUT_FOLDER.glob('*.pdf')

# Plot pdf name <trace_name>_<feature>-<feature>_<min-max (range)>.pdf
RANGES = 
for trace in TRACE_FOLDER.glob('*.csv'):
    for Xfeature, _ in FEATURES:
        for Yfeature, _ in FEATURES:
            if Xfeature == Yfeature: continue

            for

def check():
    """
    Checks if the 'trace/' folder exists. If not, creates it and prompts the user to download traces.
    Returns True if traces are ready (folder exists and has *.trace files), False otherwise.
    """
    try:
        if not OUTPUT_FOLDER.exists():
            OUTPUT_FOLDER.mkdir(parents = True, exist_ok = True)
            logging.info(f"Folder '{OUTPUT_FOLDER}/' does not exist. Creating it now...")
            logging.debug("Please restart the program.")
            return

        else:
            for 

            logging.info(f"Folder '{OUTPUT_FOLDER}/' exists. Proceed with checking files...")

            pdfs = (pdf.stem for pdf in AVAILABLE_GRAPHS)

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

def automate_plotting():
    """
    Automates plotting from CSV files in the output folder.
    - Groups CSVs by trace and range (assuming filename format: Out_{trace}_{algo}_{range}.csv or similar).
    - Plots algorithms for the same trace/range on one figure, distinguished by color and marker (for line/scatter).
    - Supports modular plot types: 'line', 'scatter', 'bar' (extendable).
    - X: frame_size (default col 0), Y: fault_rate (default col -1).
    - Saves plots as PNG in the output folder.
    
    Example usage:
    automate_plotting(output_folder='output', plot_type='line')
    automate_plotting(output_folder='output', plot_type='scatter')
    """
    # Color and marker cycles (for distinguishing algos)
    colors = cycle(['b', 'g', 'r', 'c', 'm', 'y', 'k'])
    markers = cycle(['o', 'v', '^', '<', '>', 's', 'p', '*', 'h', 'H', 'D'])

    # Find all CSV files (assuming they end with .csv)
    csv_files = DATA_FOLDER.glob("*.csv")

    # Group by trace_range (key = trace_range)
    groups = {}
    try:
        logging.info("Parsing all CSVs.")
        for file in csv_files:
            basename = os.path.basename(file)
            parts = basename.rsplit('.', 1)[0].split('_')  # Remove .csv and split by _
            if len(parts) >= 4:  # Assuming format like Out_trace_algo_range (adjust if different)
                prefix, trace, algo, rng = parts[:4]  # Handle 'Out_' prefix
                key = f"{trace}_{rng}"
                if key not in groups:
                    groups[key] = []
                groups[key].append((algo, file))
            else:
                raise Exception(f"Skipping file with unexpected name: {basename}")
    except Exception as e:
        logging.error(e)

    # For each group, create and save a plot
    for key, algo_files in groups.items():
        fig_line, ax_line = plt.subplots(figsize=(10, 6))  # Adjustable size
        fig_scatter, ax_scatter = plt.subplots(figsize=(10, 6))  # Adjustable size
        trace, rng = key.split('_')

        # Sort algos for consistent order (e.g., alphabetical)
        algo_files.sort(key=lambda x: x[0])

        for algo, file in algo_files:
            data = np.genfromtxt(file, delimiter=',')
            X = data[:, FEATURES['fs']]
            Y = data[:, FEATURES['pfr']]
            color = next(colors)
            marker = next(markers)

            # Plot based on type
            ax_line(X, Y, color=color, label=algo, linewidth=0.8)
            ax_scatter(X, Y, color=color, label=algo, s=8, marker=marker)

        # Add labels, title, legend
        ax_line.set_xlabel(r'Frame Size', size=12)
        ax_line.set_ylabel(r'Page Fault Rate', size=12)
        ax_line.set_title(rf"Page Fault Rate vs Frame Size for {trace.capitalize()} ({rng})", size=15)
        ax_line.legend(title='Algorithms')
        ax_line.grid(True)  # Optional: add grid for readability

        ax_scatter.set_xlabel(r'Frame Size', size=12)
        ax_scatter.set_ylabel(r'Page Fault Rate', size=12)
        ax_scatter.set_title(rf"Page Fault Rate vs Frame Size for {trace.capitalize()} ({rng})", size=15)
        ax_scatter.legend(title='Algorithms')
        ax_scatter.grid(True)  # Optional: add grid for readability

        # Save each figure separately
        save_line = os.path.join(OUTPUT_FOLDER, f"{trace}_{rng}_line.pdf")
        save_scatter = os.path.join(OUTPUT_FOLDER, f"{trace}_{rng}_scatter.pdf")

        fig_line.savefig(save_line, format='pdf', bbox_inches='tight')
        fig_scatter.savefig(save_scatter, format='pdf', bbox_inches='tight')

        logging.info(f"Saved: {save_line}")
        logging.info(f"Saved: {save_scatter}")

        plt.close(fig_line)
        plt.close(fig_scatter)
