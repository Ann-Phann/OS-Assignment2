#!/usr/bin/env python3
"""
clean_output_csvs.py

Sort and deduplicate all CSV files in the output folder.

CSV format expected (no header):
<frame_size>,<trace_size>,<total_disk_read>,<total_disk_write>,<page_fault_rate>

Default behaviour:
 - Sort by frame_size (ascending)
 - For duplicate frame_size rows keep the LAST occurrence
 - Backup the original file as filename.bak.YYYYMMDD-HHMMSS (unless --no-backup)

Usage:
    python clean_output_csvs.py
    python clean_output_csvs.py --folder output --keep min_pfr
    python clean_output_csvs.py --folder output --no-backup --keep first
"""
from pathlib import Path
import argparse
import logging
import shutil
import time
from datetime import datetime

try:
    import pandas as pd
except Exception as e:
    raise SystemExit("This script requires pandas. Install with: pip install pandas") from e

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

DEFAULT_FOLDER = Path("output")
EXPECTED_COLS = 5
COL_NAMES = ['frame', 'trace_size', 'total_disk_read', 'total_disk_write', 'pfr']


def backup_file(path: Path) -> Path:
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    bak = path.with_suffix(path.suffix + f".bak.{ts}")
    shutil.copy2(path, bak)
    return bak


def clean_file(path: Path, keep_strategy: str = "last", do_backup: bool = True) -> dict:
    """
    Clean one CSV file:
      - read first 5 columns (ignore extras)
      - drop rows with missing frame
      - sort by frame
      - detect duplicates (same frame)
      - remove duplicates according to keep_strategy
      - write back (overwriting original)
    Returns statistics dict.
    """
    stats = {"file": str(path), "rows_before": 0, "rows_after": 0, "duplicates_found": 0, "duplicates_removed": 0, "kept_strategy": keep_strategy, "skipped": False}

    # read CSV (be tolerant: spaces after commas)
    try:
        df = pd.read_csv(path, header=None, usecols=list(range(EXPECTED_COLS)),
                         names=COL_NAMES, engine='python', skipinitialspace=True)
    except Exception as e:
        logging.error("Failed to read %s: %s", path.name, e)
        stats["skipped"] = True
        return stats

    # drop completely empty rows
    df = df.dropna(how='all')
    if df.empty:
        logging.info("File %s is empty after dropping blank rows — skipping", path.name)
        stats["skipped"] = True
        return stats

    stats["rows_before"] = len(df)

    # ensure types: frame -> int where possible, pfr -> float
    # coerce errors to NaN then drop rows missing frame
    df['frame'] = pd.to_numeric(df['frame'], errors='coerce')
    df['pfr'] = pd.to_numeric(df['pfr'], errors='coerce')
    df = df.dropna(subset=['frame'])  # rows without frame are invalid
    df['frame'] = df['frame'].astype(int)

    # sort by frame so duplicates are adjacent
    df_sorted = df.sort_values(by='frame', ascending=True).reset_index(drop=True)

    # count duplicates (frames that appear more than once)
    dup_mask = df_sorted.duplicated(subset='frame', keep=False)
    duplicates_found = int(dup_mask.sum())
    stats["duplicates_found"] = duplicates_found

    if duplicates_found == 0:
        # just ensure file is sorted and write back (no duplicates)
        stats["rows_after"] = len(df_sorted)
        if do_backup:
            bak = backup_file(path)
            logging.info("Backup %s -> %s", path.name, bak.name)
        df_sorted.to_csv(path, index=False, header=False)
        logging.info("Sorted (no duplicates) and wrote back: %s (rows=%d)", path.name, stats["rows_after"])
        return stats

    # Deduplicate according to strategy
    if keep_strategy == "first":
        df_clean = df_sorted.drop_duplicates(subset='frame', keep='first').copy()
    elif keep_strategy == "last":
        df_clean = df_sorted.drop_duplicates(subset='frame', keep='last').copy()
    elif keep_strategy == "min_pfr":
        # for each frame, keep the row with minimum pfr
        df_clean = df_sorted.sort_values(['frame', 'pfr'], ascending=[True, True]).drop_duplicates('frame', keep='first').copy()
    elif keep_strategy == "max_pfr":
        df_clean = df_sorted.sort_values(['frame', 'pfr'], ascending=[True, False]).drop_duplicates('frame', keep='first').copy()
    else:
        raise ValueError("Unknown keep strategy: " + keep_strategy)

    df_clean = df_clean.sort_values('frame', ascending=True).reset_index(drop=True)
    stats["rows_after"] = len(df_clean)
    stats["duplicates_removed"] = stats["rows_before"] - stats["rows_after"]

    # backup original
    if do_backup:
        bak = backup_file(path)
        logging.info("Backup %s -> %s", path.name, bak.name)

    # write cleaned CSV (no header)
    df_clean.to_csv(path, index=False, header=False)
    logging.info("Cleaned %s: before=%d after=%d duplicates=%d removed=%d (kept=%s)",
                 path.name, stats["rows_before"], stats["rows_after"],
                 stats["duplicates_found"], stats["duplicates_removed"], keep_strategy)
    return stats


def main(folder: Path, keep: str = "last", no_backup: bool = False):
    folder = Path(folder)
    if not folder.exists():
        raise SystemExit(f"Folder {folder} does not exist")

    csv_files = sorted(folder.glob("*.csv"))
    if not csv_files:
        logging.info("No CSV files found in %s. Nothing to do.", folder)
        return

    totals = {"files": 0, "rows_before": 0, "rows_after": 0, "duplicates_found": 0, "duplicates_removed": 0}

    for f in csv_files:
        totals["files"] += 1
        stats = clean_file(f, keep_strategy=keep, do_backup=(not no_backup))
        if stats.get("skipped"):
            continue
        totals["rows_before"] += stats["rows_before"]
        totals["rows_after"] += stats["rows_after"]
        totals["duplicates_found"] += stats["duplicates_found"]
        totals["duplicates_removed"] += stats["duplicates_removed"]

    # summary
    logging.info("Processed %d files in %s", totals["files"], folder)
    logging.info("Total rows before: %d, after: %d", totals["rows_before"], totals["rows_after"])
    logging.info("Total duplicate rows detected: %d", totals["duplicates_found"])
    logging.info("Total duplicate rows removed: %d", totals["duplicates_removed"])
    logging.info("Done. Files in-place have been overwritten with cleaned versions (backups created unless --no-backup).")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sort and deduplicate CSVs in a folder (output/).")
    parser.add_argument("--folder", "-f", default=str(DEFAULT_FOLDER), help="Folder containing CSV files (default: output/)")
    parser.add_argument("--keep", "-k", choices=["first", "last", "min_pfr", "max_pfr"], default="last",
                        help="How to choose which duplicate row to keep. Default: last (keep the last occurrence).")
    parser.add_argument("--no-backup", action="store_true", help="Don't create .bak timestamped backups before overwriting.")
    args = parser.parse_args()
    main(Path(args.folder), keep=args.keep, no_backup=args.no_backup)
