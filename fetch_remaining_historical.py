import os
import sys
import datetime

# Setup import paths
scripts_dir = os.path.dirname(os.path.abspath(__file__))
if scripts_dir not in sys.path:
    sys.path.append(scripts_dir)

import pipeline.fetch_copernicus as fc
from pipeline.config import PIPELINE_CONFIG
from pipeline.build_mesh import build_european_mesh

def fetch_and_build_remaining():
    # Store the original execution function
    original_execute = fc._execute_download
    
    # Mock the execution function to override dates AND force dataset_id
    def mock_execute(product_id, out_dir, nc_vars, start_date_str, end_date_str, bbox, max_depth=None):
        import pandas as pd
        t_start = pd.Timestamp("2026-04-01 00:00:00")
        t_end = pd.Timestamp("2026-05-31 23:59:59")
        
        success = True
        current_start = t_start
        while current_start <= t_end:
            current_end = current_start + pd.Timedelta(days=4, hours=23, minutes=59, seconds=59)
            if current_end > t_end:
                current_end = t_end
                
            # If the chunk is in April, force MY. If it's in May, use original (NRT/ANFC)
            # because MY datasets usually don't reach May yet.
            if current_start < pd.Timestamp("2026-05-01"):
                fallback_id = product_id
                if "_anfc_" in fallback_id:
                    fallback_id = fallback_id.replace("_anfc_", "_my_")
                elif "_nrt_" in fallback_id:
                    fallback_id = fallback_id.replace("_nrt_", "_my_")
                elif "_NRT_" in fallback_id:
                    fallback_id = fallback_id.replace("_NRT_", "_REP_")
                print(f"Forcing dataset_id from {product_id} to {fallback_id} for {current_start.date()}")
            else:
                fallback_id = product_id
                print(f"Using original dataset_id {product_id} for {current_start.date()}")
                
            print(f"  Chunking download: {current_start} to {current_end}")
            try:
                res = original_execute(fallback_id, out_dir, nc_vars, 
                                       current_start.strftime("%Y-%m-%d %H:%M:%S"), 
                                       current_end.strftime("%Y-%m-%d %H:%M:%S"), 
                                       bbox, max_depth)
                if not res:
                    success = False
            except Exception as e:
                print(f"  Failed chunk: {e}")
                success = False
                
            current_start += pd.Timedelta(days=5)
            
        return success
    
    # Apply mock
    fc._execute_download = mock_execute
    
    # Variables to process (missing daily data for April and May)
    vars_to_process = ["sst", "chl", "waves", "sal", "cur"]
    
    for v in vars_to_process:
        print(f"\n{'='*50}\nProcessing Variable: {v}\n{'='*50}")
        print(f"Downloading {v} data...")
        fc.download_variable(v, PIPELINE_CONFIG, days_history=1)
        
        print(f"Building mesh for {v}...")
        # Build 2D surface meshes
        build_european_mesh(v, PIPELINE_CONFIG, historical=True)

if __name__ == "__main__":
    fetch_and_build_remaining()
