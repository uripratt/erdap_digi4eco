import os
import sys

scripts_dir = os.path.dirname(os.path.abspath(__file__))
if scripts_dir not in sys.path:
    sys.path.append(scripts_dir)

import pipeline.fetch_copernicus as fc
from pipeline.config import PIPELINE_CONFIG
from pipeline.build_mesh import build_european_mesh

def run_historical():
    # Only the ones that were incomplete or failing
    vars_to_process = ["chl", "waves", "sal", "cur"]
    
    original_execute = fc._execute_download
    
    def mock_execute(product_id, out_dir, nc_vars, start_date_str, end_date_str, bbox, max_depth=None):
        start_date_str = "2026-04-01 00:00:00"
        end_date_str = "2026-05-31 23:59:59"
        # The original _execute_download already handles the try-except and fallback to _my_
        return original_execute(product_id, out_dir, nc_vars, start_date_str, end_date_str, bbox, max_depth)
        
    fc._execute_download = mock_execute
    
    for v in vars_to_process:
        print(f"\n==================================================")
        print(f"Processing Variable: {v}")
        print(f"==================================================")
        # This triggers the download for all regions in config
        fc.download_variable(v, PIPELINE_CONFIG, days_history=1)
        
        # This processes the raw files and builds the consolidated daily/monthly NetCDFs
        print(f"Building mesh for {v}")
        try:
            build_european_mesh(v, PIPELINE_CONFIG, historical=True)
        except Exception as e:
            print(f"Error building mesh for {v}: {e}")

if __name__ == "__main__":
    run_historical()
