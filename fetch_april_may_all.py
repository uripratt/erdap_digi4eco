import os
import sys

# Setup import paths
scripts_dir = os.path.dirname(os.path.abspath(__file__))
if scripts_dir not in sys.path:
    sys.path.append(scripts_dir)

import pipeline.fetch_copernicus as fc
from pipeline.config import PIPELINE_CONFIG_HOURLY
from pipeline.build_mesh import build_european_mesh

# All 6 variables — using PIPELINE_CONFIG_HOURLY (PT1H).
# Output goes to unified_europe_hourly_* folders (no conflict with existing daily files).
VARS_TO_PROCESS = ["sst", "chl", "waves", "temp_3d", "sal", "cur"]

# Download month by month to avoid Copernicus server timeouts.
# Large PT1H requests (2 months at once) caused indefinite hang at 17%.
MONTHS = [
    ("2026-04-01 00:00:00", "2026-04-30 23:59:59", "202604"),
    ("2026-05-01 00:00:00", "2026-05-31 23:59:59", "202605"),
]

def fetch_and_build_april_may():
    original_execute = fc._execute_download

    for start_str, end_str, month_label in MONTHS:
        print(f"\n{'#'*50}")
        print(f"# MONTH: {month_label}  ({start_str[:10]} → {end_str[:10]})")
        print(f"{'#'*50}")

        # Patch download function to force the current month's date range
        def mock_execute(product_id, out_dir, nc_vars, _s, _e, bbox, max_depth=None,
                         _start=start_str, _end=end_str):
            return original_execute(product_id, out_dir, nc_vars, _start, _end, bbox, max_depth)

        fc._execute_download = mock_execute

        for v in VARS_TO_PROCESS:
            print(f"\n{'='*50}\nProcessing Variable: {v}  [{month_label}]\n{'='*50}")
            print(f"Downloading {v} data...")
            fc.download_variable(v, PIPELINE_CONFIG_HOURLY, days_history=1)

            print(f"Building mesh for {v}...")
            build_european_mesh(v, PIPELINE_CONFIG_HOURLY, historical=True)

        # Restore original after each month (safety)
        fc._execute_download = original_execute

if __name__ == "__main__":
    fetch_and_build_april_may()

