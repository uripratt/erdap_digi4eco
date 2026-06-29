import os
import sys

# Setup import paths
scripts_dir = os.path.dirname(os.path.abspath(__file__))
if scripts_dir not in sys.path:
    sys.path.append(scripts_dir)

import pipeline.fetch_copernicus as fc
from pipeline.config import PIPELINE_CONFIG_HOURLY
from pipeline.build_mesh import build_european_mesh

# ── RESUME STATE ──────────────────────────────────────────────────────────────
# SST 202604: DONE (mesh written)
# CHL 202604: killed mid-download → restart from CHL
# 202605: nothing done yet → all vars including SST
# ─────────────────────────────────────────────────────────────────────────────

PHASES = [
    # (start, end, label, vars_to_run)
    ("2026-04-01 00:00:00", "2026-04-30 23:59:59", "202604",
     ["sst", "chl", "waves", "temp_3d", "sal", "cur"]),
    ("2026-05-01 00:00:00", "2026-05-31 23:59:59", "202605",
     ["sst", "chl", "waves", "temp_3d", "sal", "cur"]),  # all vars for May
]

def fetch_and_build_april_may():
    original_execute = fc._execute_download

    for start_str, end_str, month_label, vars_to_process in PHASES:
        print(f"\n{'#'*50}", flush=True)
        print(f"# MONTH: {month_label}  ({start_str[:10]} → {end_str[:10]})", flush=True)
        print(f"# Variables: {vars_to_process}", flush=True)
        print(f"{'#'*50}", flush=True)

        def mock_execute(product_id, out_dir, nc_vars, _s, _e, bbox, max_depth=None,
                         _start=start_str, _end=end_str):
            import pandas as pd
            t_start = pd.Timestamp(_start)
            t_end = pd.Timestamp(_end)
            
            current = t_start
            while current <= t_end:
                # 7-day chunks to prevent OOM in copernicusmarine
                chunk_end = current + pd.Timedelta(days=6)
                # Ensure we end exactly at 23:59:59 of the chunk_end day
                chunk_end = chunk_end.replace(hour=23, minute=59, second=59)
                
                if chunk_end > t_end:
                    chunk_end = t_end
                
                c_start_str = current.strftime("%Y-%m-%d %H:%M:%S")
                c_end_str = chunk_end.strftime("%Y-%m-%d %H:%M:%S")
                print(f"\n      >>> Downloading Sub-chunk: {c_start_str} to {c_end_str} <<<", flush=True)
                
                original_execute(product_id, out_dir, nc_vars, c_start_str, c_end_str, bbox, max_depth)
                
                current = (chunk_end + pd.Timedelta(seconds=1)).normalize()

        fc._execute_download = mock_execute

        for v in vars_to_process:
            print(f"\n{'='*50}\nProcessing Variable: {v}  [{month_label}]\n{'='*50}", flush=True)
            print(f"Downloading {v} data...", flush=True)
            fc.download_variable(v, PIPELINE_CONFIG_HOURLY, days_history=1)

            print(f"Building mesh for {v}...", flush=True)
            build_european_mesh(v, PIPELINE_CONFIG_HOURLY, historical=True)

        fc._execute_download = original_execute

if __name__ == "__main__":
    fetch_and_build_april_may()
