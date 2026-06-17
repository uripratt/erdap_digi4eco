import os
import sys

# Setup import paths
scripts_dir = os.path.dirname(os.path.abspath(__file__))
if scripts_dir not in sys.path:
    sys.path.append(scripts_dir)

import pipeline.fetch_copernicus as fc
from pipeline.config import PIPELINE_CONFIG
from pipeline.build_mesh import build_european_mesh

def resume_april_may():
    print("==================================================")
    print("Resuming from: Building mesh for SST")
    print("==================================================")
    
    # Store the original execution function to mock dates
    original_execute = fc._execute_download
    
    def mock_execute(product_id, out_dir, nc_vars, start_date_str, end_date_str, bbox, max_depth=None):
        start_date_str = "2026-04-01 00:00:00"
        end_date_str = "2026-05-31 23:59:59"
        return original_execute(product_id, out_dir, nc_vars, start_date_str, end_date_str, bbox, max_depth)
    
    fc._execute_download = mock_execute

    # 1. Finish the SST processing (building mesh)
    build_european_mesh("sst", PIPELINE_CONFIG, historical=True)
    
    # 2. Process the remaining variables
    vars_to_process = ["waves", "temp_3d", "sal", "cur"]
    
    for v in vars_to_process:
        print(f"\n{'='*50}\nProcessing Variable: {v}\n{'='*50}")
        print(f"Downloading {v} data...")
        fc.download_variable(v, PIPELINE_CONFIG, days_history=1)
        
        print(f"Building mesh for {v}...")
        # Build 2D surface meshes
        build_european_mesh(v, PIPELINE_CONFIG, historical=True)

if __name__ == "__main__":
    resume_april_may()
