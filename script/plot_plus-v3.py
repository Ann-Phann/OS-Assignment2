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
TRACE_FOLDER = Path('trace') # Not used for CSVs, but kept for consistency
FEATURES = {
    'fs': 0, # Frame size
    'tdr': 2, # Total disk read
    'tdw': 3, # Total disk write
    'pfr': -1 # Page fault rate
}
# Get pairwise unique feature combinations (no duplicates, x != y)
FEATURE_PAIRS = list(combinations(FEATURES.keys(), 2))
PLOT_TYPES = ['line', 'scatter'] # Supported plot types
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
    data_dict = {} # range_str -> trace -> algo -> np.array
    csv_files = list(DATA_FOLDER.glob('Out_*.csv')) # Only matching format
    for file in csv_files:
        basename = file.stem # Without .csv
        if basename.startswith('Out_'):
            parts = basename[4:].split('_') # Skip 'Out_', split trace_algo_range
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
def plot_group(ax, data_group, x_feature, y_feature, plot_type, label_prefix='', data_start=None, data_end=None, show_legend=True):
    """Plot a group of data (multiple algos/traces) on one axes. Removed fig from params as not used."""
    # Color and marker cycles
    colors = cycle(['b', 'g', 'r', 'c', 'm', 'y', 'k'])
    markers = cycle(['o', 'v', '^', '<', '>', 's', 'p', '*', 'h', 'H', 'D'])
    for label, data in sorted(data_group.items()): # Sort for consistent order
        if data_start is not None or data_end is not None:
            data = data[data_start:data_end]
        X = data[:, FEATURES[x_feature]]
        Y = data[:, FEATURES[y_feature]]
        color = next(colors)
        if plot_type == 'line':
            ax.plot(X, Y, color=color, label=f"{label_prefix}{label}", linewidth=0.8)
        elif plot_type == 'scatter':
            marker = next(markers)
            ax.scatter(X, Y, color=color, label=f"{label_prefix}{label}", s=8, marker=marker)
    if show_legend:
        ax.legend(title='Items', loc='upper right')  # Place legend inside the plot area
    ax.grid(True)
def automate_plotting(mode='single-trace-algo', num_traces=None, num_algos=None, data_start=None, data_end=None):
    """
    Automates plotting based on mode.
    - Modes:
        - 'combined-trace-algo': All traces and algos in one figure per range/pair/type (if >=2 traces/algos).
        - 'combined-trace-single-algo': All traces per figure, but one algo per plot.
        - 'single-trace-algo': One trace per figure, all algos.
        - 'single-algo-single-trace': One trace and one algo per figure.
    - num_traces/num_algos: Limit for combined modes (e.g., top N by name sort).
    - data_start/data_end: Optional row indices to slice data from CSVs (e.g., data_start=1000, data_end=4096).
    - Checks for existing PDFs and skips if present.
    - Logs counts of existing/needed PDFs.
    """
    data_dict = load_csv_data()
    total_needed = 0
    total_existing = 0
    produced = 0
    slice_suffix = ''
    if data_start is not None or data_end is not None:
        start_val = data_start if data_start is not None else 0
        end_val = data_end if data_end is not None else 'end'
        slice_suffix = f"_slice_{start_val}-{end_val}"
    # Calculate total possible based on mode
    for range_str in data_dict:
        traces = sorted(data_dict[range_str].keys())
        algos = set() # Unique algos across traces
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
                    name_parts = [f"combined_traces_algos_{range_str}_{x_feature}-{y_feature}_{plot_type}{slice_suffix}"]
                elif mode == 'combined-trace-single-algo':
                    # One plot per algo, all traces
                    name_parts = []
                    selected_algos = algos[:num_algos] if num_algos is not None else algos
                    for algo in selected_algos:
                        name_parts.append(f"combined_traces_{algo}_{range_str}_{x_feature}-{y_feature}_{plot_type}{slice_suffix}")
                elif mode == 'single-trace-algo':
                    # One plot per trace, all algos
                    selected_traces = traces[:num_traces] if num_traces is not None else traces
                    name_parts = [f"{trace}_algos_{range_str}_{x_feature}-{y_feature}_{plot_type}{slice_suffix}" for trace in selected_traces]
                elif mode == 'single-algo-single-trace':
                    # One plot per trace-algo pair
                    name_parts = []
                    selected_traces = traces[:num_traces] if num_traces is not None else traces
                    selected_algos = algos[:num_algos] if num_algos is not None else algos
                    for trace in selected_traces:
                        for algo in selected_algos:
                            if algo in data_dict[range_str].get(trace, {}):
                                name_parts.append(f"{trace}_{algo}_{range_str}_{x_feature}-{y_feature}_{plot_type}{slice_suffix}")
                else:
                    raise ValueError(f"Unknown mode: {mode}")
                for base_name in name_parts:
                    pdf_path = OUTPUT_FOLDER / f"{base_name}.pdf"
                    total_needed += 1
                    if pdf_path.exists():
                        total_existing += 1
                        continue
                    # Plot only if missing
                    selected_traces = traces[:num_traces] if num_traces is not None else traces
                    num_subplots = len(selected_traces) if mode.startswith('combined') else 1
                    fig = plt.figure(figsize=(3 * num_subplots, 6))
                    if num_subplots > 1:
                        axs = fig.subplots(2, int(num_subplots / 2), sharey=True, sharex=True) # Share y for comparison
                    else:
                        axs = fig.add_subplot(111)
                    if isinstance(axs, np.ndarray):
                        axs = axs.flatten()
                    else:
                        axs = [axs]
                    if mode == 'combined-trace-algo':
                        # One fig, subplots per trace, each with algos
                        for i, trace in enumerate(selected_traces):
                            ax = axs[i]
                            all_data = data_dict[range_str][trace]
                            selected_algos = algos[:num_algos] if num_algos is not None else algos
                            selected_data = {algo: all_data[algo] for algo in selected_algos if algo in all_data}
                            plot_group(ax, selected_data, x_feature, y_feature, plot_type, label_prefix='Algo: ', data_start=data_start, data_end=data_end, show_legend=(i == 0))
                            ax.set_title(rf"{trace.capitalize()}")
                            ax.set_xlabel(get_feature_label(x_feature), size=11)
                            if i == 0:
                                ax.set_ylabel(get_feature_label(y_feature), size=11)
                    elif mode == 'combined-trace-single-algo':
                        # One fig per algo, subplots per trace, each with single algo
                        parts = base_name.split('_')
                        algo = parts[2] # combined_traces_{algo}_...
                        for i, trace in enumerate(selected_traces):
                            ax = axs[i]
                            if algo in data_dict[range_str].get(trace, {}):
                                single_data = {algo: data_dict[range_str][trace][algo]}
                                plot_group(ax, single_data, x_feature, y_feature, plot_type, data_start=data_start, data_end=data_end, show_legend=(i == 0))
                            ax.set_title(rf"{trace.capitalize()} ({algo})")
                            ax.set_xlabel(get_feature_label(x_feature), size=11)
                            if i == 0:
                                ax.set_ylabel(get_feature_label(y_feature), size=11)
                    elif mode == 'single-trace-algo':
                        # Single fig/ax per trace
                        parts = base_name.split('_')
                        trace = parts[0]
                        ax = axs[0]
                        all_data = data_dict[range_str][trace]
                        selected_algos = algos[:num_algos] if num_algos is not None else algos
                        selected_data = {algo: all_data[algo] for algo in selected_algos if algo in all_data}
                        plot_group(ax, selected_data, x_feature, y_feature, plot_type, label_prefix='Algo: ', data_start=data_start, data_end=data_end)
                        ax.set_title(rf"{trace.capitalize()} ({get_feature_label(y_feature)} vs {get_feature_label(x_feature)})")
                        ax.set_xlabel(get_feature_label(x_feature), size=11)
                        ax.set_ylabel(get_feature_label(y_feature), size=11)
                    elif mode == 'single-algo-single-trace':
                        # Single fig/ax per trace-algo
                        parts = base_name.split('_')
                        trace = parts[0]
                        algo = parts[1]
                        ax = axs[0]
                        data = data_dict[range_str][trace][algo]
                        if data_start is not None or data_end is not None:
                            data = data[data_start:data_end]
                        X = data[:, FEATURES[x_feature]]
                        Y = data[:, FEATURES[y_feature]]
                        if plot_type == 'line':
                            ax.plot(X, Y, label=f"{trace}_{algo}")
                        elif plot_type == 'scatter':
                            ax.scatter(X, Y, label=f"{trace}_{algo}")
                        ax.legend(loc='upper left')  # Inside for single plots
                        ax.set_title(rf"{trace.capitalize()} {algo} ({get_feature_label(y_feature)} vs {get_feature_label(x_feature)})")
                        ax.set_xlabel(get_feature_label(x_feature), size=11)
                        ax.set_ylabel(get_feature_label(y_feature), size=11)
                    fig.suptitle(rf"{start_val}-{end_val} data slice, {get_feature_label(y_feature)} vs {get_feature_label(x_feature)}", size=15)
                    fig.tight_layout(rect=[0, 0.03, 1, 0.95])  # Adjust layout to leave space for suptitle
                    fig.savefig(pdf_path, format='pdf', bbox_inches='tight')
                    plt.close(fig)
                    produced += 1
    logging.info(f"Total PDFs needed: {total_needed}")
    logging.info(f"Existing PDFs: {total_existing}")
    logging.info(f"New PDFs produced: {produced}")
if __name__ == "__main__":
    OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)
    # Example calls; adjust as needed
    automate_plotting(mode='combined-trace-algo', data_start=1, data_end=200)
    automate_plotting(mode='combined-trace-algo', data_start=1, data_end=4096)
    automate_plotting(mode='combined-trace-algo', data_start=1000, data_end=4096)
    automate_plotting(mode='combined-trace-algo', data_start=200, data_end=500)
    automate_plotting(mode='combined-trace-algo', data_start=500, data_end=700)
    automate_plotting(mode='combined-trace-algo', data_start=3800, data_end=4096)
    # automate_plotting(mode='combined-trace-algo', num_traces=4, num_algos=3)
    # etc.