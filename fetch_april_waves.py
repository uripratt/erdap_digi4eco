import os
import datetime
from pipeline.config import PIPELINE_CONFIG
from pipeline.fetch_copernicus import download_variable
from pipeline.build_mesh import build_european_mesh

def fetch_april_waves():
    import pipeline.fetch_copernicus as fc
    
    original_execute = fc._execute_download
    
    def mock_execute(product_id, out_dir, nc_vars, start_date_str, end_date_str, bbox, max_depth=None):
        start_date_str = "2026-04-15 00:00:00"
        end_date_str = "2026-04-16 00:00:00"
        return original_execute(product_id, out_dir, nc_vars, start_date_str, end_date_str, bbox, max_depth)
    
    fc._execute_download = mock_execute
    
    print("Downloading April waves data...")
    fc.download_variable("waves", PIPELINE_CONFIG, days_history=1)
    
    print("Building mesh for waves...")
    build_european_mesh("waves", PIPELINE_CONFIG, historical=True)

if __name__ == "__main__":
    fetch_april_waves()
