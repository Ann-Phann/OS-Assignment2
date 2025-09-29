from matplotlib import rc
from pathlib import Path
from itertools import cycle, combinations
import matplotlib.pyplot as plt
import numpy as np
import os
import logging
from matplotlib.lines import Line2D

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s [%(levelname)s] %(message)s',
                    datefmt='%Y-%m-%d %H:%M')
logging.getLogger('matplotlib').setLevel(logging.WARNING)

rc('font', **{'family': 'serif', 'serif': ['Computer Modern']})
rc('text', usetex=True)

OUTPUT_FOLDER = Path("graph")
DATA_FOLDER = Path("output")

FEATURES = {
    'fs': 0,   # Frame size (x-axis index in CSV rows)
    'tdr': 2,  # Total disk read
    'tdw': 3,  # Total disk write
    'pfr': -1  # Page fault rate
}

# Fixed algorithm order and colors (keeps consistent mapping across plots)
ALGO_ORDER = ['lru', 'rand', 'clock', 'optimal']
ALGO_COLORS = {
    'lru': 'tab:blue',
    'rand': 'tab:green',
    'clock': 'tab:red',
    'optimal': 'tab:purple'
}

PLOT_TYPES = ['line', 'scatter']  # Supported plot types

def get_feature_label(feature):
    labels = {
        'fs': r'Frame Size',
        'tdr': r'Total Disk Reads',
        'tdw': r'Total Disk Writes',
        'pfr': r'Page Fault Rate'
    }
    return labels.get(feature, feature)

def load_csv_data():
    """
    Load and group all CSV data by range -> trace -> algo -> numpy array.
    Expects filenames like Out_<trace>_<algo>_<range>.csv
    """
    data_dict = {}
    csv_files = list(DATA_FOLDER.glob('Out_*.csv'))
    for file in csv_files:
        basename = file.stem
        if basename.startswith('Out_'):
            parts = basename[4:].split('_')  # trace_algo_range
            if len(parts) == 3:
                trace, algo, range_str = parts
                data_dict.setdefault(range_str, {}).setdefault(trace, {})[algo] = None
                try:
                    data = np.genfromtxt(file, delimiter=',')
                    data_dict[range_str][trace][algo] = data
                    logging.debug(f"Loaded {file}")
                except Exception as e:
                    logging.error(f"Error loading {file}: {e}")
            else:
                logging.warning(f"Skipping invalid filename: {file}")
    return data_dict

def _safe_slice(data, start_one_based, end_one_based):
    """
    Convert 1-based inclusive slice (start,end) to python slice [start0:end0).
    Returns the sliced array or empty array if out-of-range.
    """
    if data is None or data.size == 0:
        return np.empty((0,))
    nrows = data.shape[0]
    start_idx = max(0, int(start_one_based) - 1)
    end_idx = int(end_one_based)
    if start_idx >= nrows:
        return np.empty((0, data.shape[1])) if data.ndim > 1 else np.empty((0,))
    end_idx = min(end_idx, nrows)
    return data[start_idx:end_idx]

def automate_plotting_slices_per_axis(data_slices,
                                      x_feature='fs',
                                      y_feature='pfr',
                                      plot_type='line'):
    """
    Create one figure per trace. Each figure contains 4 axes (2x2).
    Each axis corresponds to one data_slice (1-based inclusive). On that axis,
    plot all algorithms (lru, rand, clock, optimal) for that slice.
    Only the FIRST axis shows a legend (with all algos/colors).
    """
    if plot_type not in PLOT_TYPES:
        raise ValueError(f"Unsupported plot_type: {plot_type}")

    data_dict = load_csv_data()
    if not data_dict:
        logging.error("No data found in output/ (Out_*.csv). Exiting.")
        return

    slice_suffix = "_".join([f"{s}-{e}" for s, e in data_slices])
    slice_suffix = f"_slices_{slice_suffix}"

    total_needed = 0
    total_existing = 0
    produced = 0

    for range_str in sorted(data_dict.keys()):
        traces = sorted(data_dict[range_str].keys())
        for trace in traces:
            base_name = f"{trace}_ranges_{range_str}_{x_feature}-{y_feature}_{plot_type}{slice_suffix}"
            pdf_path = OUTPUT_FOLDER / f"{base_name}.pdf"
            total_needed += 1
            if pdf_path.exists():
                total_existing += 1
                continue

            # Create 2x2 grid (4 axes)
            fig, axes = plt.subplots(2, 2, figsize=(2 * 4, 7))
            axes = axes.flatten()
            all_data = data_dict[range_str].get(trace, {})

            # Plot per-axis (each slice), plotting all algos together.
            for ax_idx, sl in enumerate(data_slices):
                ax = axes[ax_idx]
                s_one, e_one = sl
                ax_has_data = False

                for algo in ALGO_ORDER:
                    data = all_data.get(algo, None)
                    if data is None:
                        continue
                    slice_data = _safe_slice(data, s_one, e_one)
                    if slice_data.size == 0:
                        continue
                    # Extract X and Y
                    try:
                        X = slice_data[:, FEATURES[x_feature]]
                        Y = slice_data[:, FEATURES[y_feature]]
                    except Exception as ex:
                        logging.error(f"Malformed data for {trace}/{algo}: {ex}")
                        continue

                    color = ALGO_COLORS.get(algo, None)
                    label = algo  # label is set but legend shown only on first axis
                    if plot_type == 'line':
                        ax.plot(X, Y, label=label, color=color, linewidth=0.9)
                    else:
                        ax.scatter(X, Y, label=label, color=color, s=12)
                    ax_has_data = True

                ax.set_title(f"{s_one + 1}-{e_one + 1}", fontsize=10)
                ax.set_xlabel(get_feature_label(x_feature), size=9)
                ax.set_ylabel(get_feature_label(y_feature), size=9)
                ax.grid(True)
                if not ax_has_data:
                    ax.text(0.5, 0.5, 'No data', ha='center', va='center', transform=ax.transAxes, fontsize=10)
                    ax.set_xticks([])
                    ax.set_yticks([])

            # if fewer than 4 slices, hide extra axes
            n_slices = len(data_slices)
            if n_slices < 4:
                for i in range(n_slices, 4):
                    axes[i].axis('off')

            # Build legend handles once (consistent order/colors) and put in FIRST axis
            legend_handles = []
            legend_labels = []
            for algo in ALGO_ORDER:
                # Create a Line2D handle for the legend (marker+line) using algo color
                color = ALGO_COLORS.get(algo, 'k')
                handle = Line2D([0], [0], color=color, lw=1, marker='o', markersize=6)
                legend_handles.append(handle)
                legend_labels.append(algo)
            # Place legend inside first axis (upper right)
            axes[0].legend(title='Algorithm', fontsize='medium',
                           loc='upper right', frameon=True)

            # fig.suptitle(rf"{trace.capitalize()} -- {get_feature_label(y_feature)} vs {get_feature_label(x_feature)}", size=12)
            fig.tight_layout(rect=[0, 0.03, 1, 0.94])
            fig.savefig(pdf_path, format='pdf', bbox_inches='tight')
            plt.close(fig)
            produced += 1

    logging.info(f"Total PDFs needed: {total_needed}")
    logging.info(f"Existing PDFs: {total_existing}")
    logging.info(f"New PDFs produced: {produced}")

if __name__ == "__main__":
    OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)

    # Example: four 1-based inclusive ranges per axis
    slices = [(0, 199), (0, 9), (9, 74), (74, 199)]
    automate_plotting_slices_per_axis(slices, x_feature='fs', y_feature='pfr', plot_type='line')