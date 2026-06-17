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
from pipeline.build_mesh_3d import build_european_mesh_3d

def fetch_and_build_april_may():
    # Store the original execution function
    original_execute = fc._execute_download
    
    # Mock the execution function to override dates
    def mock_execute(product_id, out_dir, nc_vars, start_date_str, end_date_str, bbox, max_depth=None):
        start_date_str = "2026-04-01 00:00:00"
        end_date_str = "2026-05-31 23:59:59"
        return original_execute(product_id, out_dir, nc_vars, start_date_str, end_date_str, bbox, max_depth)
    
    # Apply mock
    fc._execute_download = mock_execute
    
    # Variables to process
    vars_to_process = ["chl", "sst", "waves", "temp_3d", "sal", "cur"]
    
    for v in vars_to_process:
        print(f"\n{'='*50}\nProcessing Variable: {v}\n{'='*50}")
        print(f"Downloading {v} data...")
        fc.download_variable(v, PIPELINE_CONFIG, days_history=1)
        
        print(f"Building mesh for {v}...")
        # Build 2D surface meshes
        build_european_mesh(v, PIPELINE_CONFIG, historical=True)
        
        # Only 2D variables requested, omitting 3D mesh processing.

if __name__ == "__main__":
    fetch_and_build_april_may()
