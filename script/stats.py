#!/usr/bin/env python3
"""
compute_means_segments.py

Read Out_<trace>_<algo>_1-4096.csv files from output/ and compute mean fault_rate
for a set of 1-based inclusive segments. Write one output CSV per trace:
    output/Means_<trace_name>.csv

Output CSV format:
segment,lru,rand,clock,optimal
1-200,0.012345,0.013456,...
1-10,...

Change DEFAULT_SLICES below to change which segments are computed.
"""

from pathlib import Path
import pandas as pd
import numpy as np
import logging
import sys

# -------- user-editable defaults --------
DATA_FOLDER = Path("output")           # where the Out_*.csv files live
OUTPUT_FOLDER = DATA_FOLDER            # writing Means_<trace>.csv into same folder
# default segments as 1-based inclusive tuples (start, end)
DEFAULT_SLICES = [(1, 200), (1, 10), (10, 75), (75, 200)]
# expected algorithm column order in the output CSV
ALGO_ORDER = ['lru', 'rand', 'clock', 'optimal']
# column index for fault_rate in input CSV (0-based if using numpy) OR column name after pd.read_csv
FAULT_RATE_COL = 'fault_rate'  # we'll use pandas names below
# names used to read input CSVs (the files don't have headers)
INPUT_COL_NAMES = ['frame_size', 'trace_size', 'read', 'write', 'fault_rate']
# ----------------------------------------

# logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

def one_based_slice_to_idx(start_one, end_one):
    """
    Convert 1-based inclusive (start_one, end_one) to 0-based pandas iloc indices:
    iloc[start_idx : end_idx_exclusive] where end_idx_exclusive = end_one (since iloc excludes end idx).
    Example: (1,10) -> iloc[0:10] which picks rows 0..9 (1..10 in 1-based).
    """
    start_idx = max(0, int(start_one) - 1)
    end_idx_exc = int(end_one)   # safe: pandas iloc uses exclusive end
    return start_idx, end_idx_exc

def find_input_files(folder: Path):
    """
    Return a list of Path for files matching Out_<trace>_<algo>_1-4096.csv in folder.
    """
    pattern = "Out_*_1-4096.csv"
    return sorted(folder.glob(pattern))

def parse_trace_algo_from_name(fname: Path):
    """
    From filename stem 'Out_<trace>_<algo>_1-4096' return (trace, algo).
    If file name doesn't match expected pattern return (None, None).
    """
    stem = fname.stem
    if not stem.startswith("Out_"):
        return None, None
    parts = stem[4:].split('_')  # after 'Out_'
    if len(parts) != 3:
        return None, None
    trace, algo, rng = parts
    return trace, algo.lower()

def load_csv_file(path: Path):
    """
    Read a CSV file with no header and known columns:
    <frame_size>,<trace_size>,<read>,<write>,<fault rate>
    Return a pandas DataFrame.
    """
    try:
        # use pandas for robustness; allow for extra whitespace, missing rows, etc.
        df = pd.read_csv(path, header=None, names=INPUT_COL_NAMES, dtype=float, engine="python", on_bad_lines='skip')
        return df
    except Exception as e:
        logging.error(f"Failed to read {path}: {e}")
        return None

def compute_means_for_trace(trace_name, algo_to_df, slices):
    """
    Given mapping algo_name -> DataFrame, compute mean fault_rate for each slice.
    Return a pandas DataFrame indexed by segment label, columns = ALGO_ORDER.
    """
    results = {}
    for s in slices:
        s_label = f"{s[0]}-{s[1]}"
        results[s_label] = {}
        # compute for each algo in ALGO_ORDER (so the CSV has consistent column order)
        for algo in ALGO_ORDER:
            df = algo_to_df.get(algo)
            if df is None:
                # missing file for this algo/trace
                results[s_label][algo] = np.nan
                continue
            # convert 1-based inclusive to iloc indices
            start_idx, end_idx_exc = one_based_slice_to_idx(s[0], s[1])
            # guard: if start_idx >= len(df) -> no data
            if start_idx >= len(df):
                results[s_label][algo] = np.nan
                continue
            sub = df.iloc[start_idx:end_idx_exc]   # pandas iloc uses exclusive end
            # compute mean of fault_rate column, handle empty selection
            if sub.empty:
                results[s_label][algo] = np.nan
            else:
                # use float conversion and skip NaNs
                mean_val = sub[FAULT_RATE_COL].astype(float).mean(skipna=True)
                results[s_label][algo] = mean_val
    # build DataFrame: index=segment labels, columns=ALGO_ORDER
    out_df = pd.DataFrame.from_dict(results, orient='index')
    out_df = out_df.reindex(columns=ALGO_ORDER)  # ensure column order
    out_df.index.name = 'segment'
    return out_df

def main(slices=None):
    """
    Main orchestration:
    - find files
    - group them by trace -> algo -> DataFrame
    - compute means per trace
    - write output Means_<trace>.csv into OUTPUT_FOLDER
    """
    if slices is None:
        slices = DEFAULT_SLICES

    # ensure folders exist
    if not DATA_FOLDER.exists():
        logging.error(f"Data folder {DATA_FOLDER} does not exist. Exiting.")
        sys.exit(1)
    OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)

    files = find_input_files(DATA_FOLDER)
    if not files:
        logging.error(f"No files found in {DATA_FOLDER} matching Out_*_1-4096.csv")
        return

    # group files by trace
    traces = {}
    for f in files:
        trace, algo = parse_trace_algo_from_name(f)
        if trace is None:
            logging.warning(f"Skipping unexpected file: {f.name}")
            continue
        # read file
        df = load_csv_file(f)
        if df is None:
            logging.warning(f"Skipping unreadable file: {f.name}")
            continue
        traces.setdefault(trace, {})[algo] = df

    # compute and write Means_<trace>.csv for each trace
    for trace_name, algo_to_df in sorted(traces.items()):
        logging.info(f"Computing means for trace '{trace_name}' with algos: {sorted(algo_to_df.keys())}")
        out_df = compute_means_for_trace(trace_name, algo_to_df, slices)
        out_path = OUTPUT_FOLDER / f"Means_{trace_name}.csv"
        # write CSV: include header, float format with 6 decimals
        out_df.to_csv(out_path, float_format="%.4f")
        logging.info(f"Wrote {out_path} (rows={len(out_df)}, cols={len(out_df.columns)})")

if __name__ == "__main__":
    # Example usage: change DEFAULT_SLICES above or call main with a custom list:
    # e.g. main(slices=[(1,200),(1,10),(10,75),(75,200)])
    main()