from matplotlib import rc
from pathlib import Path
from itertools import cycle, combinations
import matplotlib.pyplot as plt
import numpy as np
import os
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M')
logging.getLogger('matplotlib').setLevel(logging.WARNING)

rc('font', **{'family': 'serif', 'serif': ['Computer Modern']})
rc('text', usetex=True)

OUTPUT_FOLDER = Path("graph")
DATA_FOLDER = Path("output")
TRACE_FOLDER = Path('trace')  # Not used for CSVs, but kept for consistency

FEATURES = {
    'fs': 0,  # Frame size
    'tdr': 2,  # Total disk read
    'tdw': 3,  # Total disk write
    'pfr': -1  # Page fault rate
}

# Get pairwise unique feature combinations (no duplicates, x != y)
FEATURE_PAIRS = list(combinations(FEATURES.keys(), 2))

PLOT_TYPES = ['line', 'scatter']  # Supported plot types

def get_feature_label(feature):
    """Map feature key to LaTeX label for axes."""
    labels = {
        'fs': r'Frame Size',
        'tdr': r'Total Disk Reads',
        'tdw': r'Total Disk Writes',
        'pfr': r'Page Fault Rate'
    }
    return labels.get(feature, feature)

def load_csv_data():
    """Load and group all CSV data by range > trace > algo."""
    data_dict = {}  # range_str -> trace -> algo -> np.array
    csv_files = list(DATA_FOLDER.glob('Out_*.csv'))  # Only matching format
    for file in csv_files:
        basename = file.stem  # Without .csv
        if basename.startswith('Out_'):
            parts = basename[4:].split('_')  # Skip 'Out_', split trace_algo_range
            if len(parts) == 3:
                trace, algo, range_str = parts
                if range_str not in data_dict:
                    data_dict[range_str] = {}
                if trace not in data_dict[range_str]:
                    data_dict[range_str][trace] = {}
                try:
                    data = np.genfromtxt(file, delimiter=',')
                    data_dict[range_str][trace][algo] = data
                    logging.debug(f"Loaded {file}")
                except Exception as e:
                    logging.error(f"Error loading {file}: {e}")
            else:
                logging.warning(f"Skipping invalid filename: {file}")
    return data_dict

def plot_group(fig, ax, data_group, x_feature, y_feature, plot_type, label_prefix=''):
    """Plot a group of data (multiple algos/traces) on one axes."""
    # Color and marker cycles
    colors = cycle(['b', 'g', 'r', 'c', 'm', 'y', 'k'])
    markers = cycle(['o', 'v', '^', '<', '>', 's', 'p', '*', 'h', 'H', 'D'])

    for label, data in sorted(data_group.items()):  # Sort for consistent order
        X = data[:, FEATURES[x_feature]]
        Y = data[:, FEATURES[y_feature]]
        color = next(colors)
        if plot_type == 'line':
            ax.plot(X, Y, color=color, label=f"{label_prefix}{label}", linewidth=0.8)
        elif plot_type == 'scatter':
            marker = next(markers)
            ax.scatter(X, Y, color=color, label=f"{label_prefix}{label}", s=8, marker=marker)
    ax.legend(title='Items')
    ax.grid(True)

def automate_plotting(mode='single-trace-algo', num_traces=None, num_algos=None):
    """
    Automates plotting based on mode.
    - Modes:
        - 'combined-trace-algo': All traces and algos in one figure per range/pair/type (if >=2 traces/algos).
        - 'combined-trace-single-algo': All traces per figure, but one algo per plot.
        - 'single-trace-algo': One trace per figure, all algos.
        - 'single-algo-single-trace': One trace and one algo per figure.
    - num_traces/num_algos: Limit for combined modes (e.g., top N by name sort).
    - Checks for existing PDFs and skips if present.
    - Logs counts of existing/needed PDFs.
    """
    data_dict = load_csv_data()
    total_needed = 0
    total_existing = 0
    produced = 0

    # Calculate total possible based on mode
    for range_str in data_dict:
        traces = sorted(data_dict[range_str].keys())
        algos = set()  # Unique algos across traces
        for trace in traces:
            algos.update(data_dict[range_str][trace].keys())
        algos = sorted(algos)

        if mode.startswith('combined') and (len(traces) < 2 or len(algos) < 2):
            logging.info(f"Skipping range {range_str} for {mode}: <2 traces/algos")
            continue

        for x_feature, y_feature in FEATURE_PAIRS:
            for plot_type in PLOT_TYPES:
                # Build filename based on mode
                if mode == 'combined-trace-algo':
                    name_parts = [f"combined_traces_algos_{range_str}_{x_feature}-{y_feature}_{plot_type}"]
                elif mode == 'combined-trace-single-algo':
                    # One plot per algo, all traces
                    for algo in (algos[:num_algos] if num_algos else algos):
                        name_parts = [f"combined_traces_{algo}_{range_str}_{x_feature}-{y_feature}_{plot_type}"]
                elif mode == 'single-trace-algo':
                    # One plot per trace, all algos
                    selected_traces = traces[:num_traces] if num_traces else traces
                    name_parts = [f"{trace}_algos_{range_str}_{x_feature}-{y_feature}_{plot_type}" for trace in selected_traces]
                elif mode == 'single-algo-single-trace':
                    # One plot per trace-algo pair
                    name_parts = []
                    selected_traces = traces[:num_traces] if num_traces else traces
                    selected_algos = algos[:num_algos] if num_algos else algos
                    for trace in selected_traces:
                        for algo in selected_algos:
                            if algo in data_dict[range_str].get(trace, {}):
                                name_parts.append(f"{trace}_{algo}_{range_str}_{x_feature}-{y_feature}_{plot_type}")
                else:
                    raise ValueError(f"Unknown mode: {mode}")

                for base_name in name_parts:
                    pdf_path = OUTPUT_FOLDER / f"{base_name}.pdf"
                    total_needed += 1
                    if pdf_path.exists():
                        total_existing += 1
                        continue
                    # Plot only if missing
                    fig, ax = plt.subplots(figsize=(10, 6))
                    if mode == 'combined-trace-algo':
                        # Flatten all trace-algo data
                        all_data = {}
                        for trace in (traces[:num_traces] if num_traces else traces):
                            for algo in (algos[:num_algos] if num_algos else algos):
                                if algo in data_dict[range_str].get(trace, {}):
                                    key = f"{trace}_{algo}"
                                    all_data[key] = data_dict[range_str][trace][algo]
                        plot_group(fig, ax, all_data, x_feature, y_feature, plot_type)
                    elif mode == 'combined-trace-single-algo':
                        # For each algo plot
                        all_data = {}
                        for trace in (traces[:num_traces] if num_traces else traces):
                            if algo in data_dict[range_str].get(trace, {}):  # algo from loop above
                                all_data[trace] = data_dict[range_str][trace][algo]
                        plot_group(fig, ax, all_data, x_feature, y_feature, plot_type, label_prefix='Trace: ')
                    elif mode == 'single-trace-algo':
                        # For each trace plot
                        all_data = data_dict[range_str][trace]  # trace from loop
                        plot_group(fig, ax, all_data, x_feature, y_feature, plot_type, label_prefix='Algo: ')
                    elif mode == 'single-algo-single-trace':
                        # Single data
                        data = data_dict[range_str][trace][algo]  # from loops
                        if plot_type == 'line':
                            ax.plot(data[:, FEATURES[x_feature]], data[:, FEATURES[y_feature]], label=f"{trace}_{algo}")
                        elif plot_type == 'scatter':
                            ax.scatter(data[:, FEATURES[x_feature]], data[:, FEATURES[y_feature]], label=f"{trace}_{algo}")
                        ax.legend()

                    # Common setup
                    ax.set_xlabel(get_feature_label(x_feature), size=12)
                    ax.set_ylabel(get_feature_label(y_feature), size=12)
                    ax.set_title(rf"{get_feature_label(y_feature)} vs {get_feature_label(x_feature)} ({mode}, {range_str})", size=15)
                    fig.savefig(pdf_path, format='pdf', bbox_inches='tight')
                    plt.close(fig)
                    produced += 1

    logging.info(f"Total PDFs needed: {total_needed}")
    logging.info(f"Existing PDFs: {total_existing}")
    logging.info(f"New PDFs produced: {produced}")

if __name__ == "__main__":
    OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)
    # Example calls; adjust as needed
    automate_plotting(mode='combined-trace-algo')
    # automate_plotting(mode='combined-trace-algo', num_traces=4, num_algos=3)
    # etc.