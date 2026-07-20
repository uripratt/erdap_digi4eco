import os
import glob
import argparse
import pandas as pd
import xarray as xr
import numpy as np
import sys
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if base_dir not in sys.path:
    sys.path.append(base_dir)

from pipeline.config import PIPELINE_CONFIG, PIPELINE_CONFIG_HOURLY

def generate_predictions(pipeline_config=None, mode="daily"):
    if pipeline_config is None:
        pipeline_config = PIPELINE_CONFIG
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    datasets_dir = os.path.join(base_dir, "datasets")
    
    # Variables to predict
    variables = ["sst", "chl", "sal_surface", "cur_surface", "waves"]
    
    # End of next month calculation
    today = pd.Timestamp.now().normalize()
    # To get the end of next month, we add 32 days to the first of next month, then go to the end of that month
    next_month_first = (today.replace(day=1) + pd.DateOffset(months=1))
    end_of_next_month = (next_month_first + pd.DateOffset(months=1)) - pd.DateOffset(days=1)
    end_date_str = end_of_next_month.strftime("%Y-%m-%d")
    
    print(f"Generating predictions up to: {end_date_str}")
    
    for var in variables:
        print(f"\n--- Processing variable: {var} ---")
        if mode == "hourly":
            folder = os.path.join(datasets_dir, f"unified_europe_hourly_{var}")
        else:
            folder = os.path.join(datasets_dir, f"unified_europe_{var}")
        if not os.path.exists(folder):
            print(f"  Folder {folder} not found, skipping.")
            continue
            
        # Find all historical monthly files (exclude prediction files)
        historical_files = sorted(glob.glob(os.path.join(folder, "*_20[0-9][0-9][0-9][0-9].nc")))
        if not historical_files:
            print("  No historical files found, skipping.")
            continue
            
        # Open the latest historical file to get the last slice
        latest_file = historical_files[-1]
        print(f"  Reading last real data from: {os.path.basename(latest_file)}")
        
        try:
            ds = xr.open_dataset(latest_file)
            if 'time' not in ds.dims or len(ds.time) == 0:
                print("  No time dimension found.")
                ds.close()
                continue
                
            # Get the very last slice
            last_slice = ds.isel(time=-1).load()
            last_time = pd.Timestamp(last_slice.time.values)
            ds.close()
            
            # Determine prediction frequency from config (temporal_res field).
            # Falls back to '1D' if not specified (standard daily mode).
            var_base = var.replace("_surface", "")  # e.g. "sal_surface" → "sal"
            conf = pipeline_config.get(var_base, {})
            temporal_res = conf.get("temporal_res", "P1D")
            freq = "1h" if temporal_res.startswith("PT") else "1D"
            
            # Generate future time array
            pred_end = end_of_next_month
            if freq == "1h":
                # For hourly mode, predicting months ahead causes OOM (~50GB RAM needed). Limit to 7 days.
                pred_end = min(end_of_next_month, last_time + pd.Timedelta(days=7))
                
            future_times = pd.date_range(start=last_time + pd.Timedelta(freq), end=pred_end, freq=freq)
            
            if len(future_times) == 0:
                print("  Data is already up to date with the prediction target.")
                continue
                
            print(f"  Generating {len(future_times)} prediction slices starting from {future_times[0]}...")
            
            # Replicate the last slice for all future times
            # We expand the dims to include the new time array
            pred_ds = last_slice.expand_dims(time=future_times)
            
            # Set data_type=2 (Prediction) on all future slices
            if 'data_type' in pred_ds.data_vars:
                pred_ds['data_type'] = xr.full_like(pred_ds['data_type'], 2, dtype=np.int8)
            elif 'prediction_flag' in pred_ds.data_vars:
                # Legacy support: rename prediction_flag to data_type
                pred_ds = pred_ds.rename({'prediction_flag': 'data_type'})
                pred_ds['data_type'] = xr.full_like(pred_ds['data_type'], 2, dtype=np.int8)
            else:
                var_name = [v for v in pred_ds.data_vars if v not in ['status_mask', 'time', 'data_type', 'prediction_flag']][0]
                pred_ds['data_type'] = xr.full_like(pred_ds[var_name], 2, dtype=np.int8)
                
            # Save the prediction file
            # We use zPREDICTION so it sorts alphanumerically after the historical files if ERDDAP uses alphabetical sorting
            # But ERDDAP primarily uses the time dimension for grid datasets.
            # Get the base resolution name (e.g. EUROPE_TOTAL_1KM)
            base_prefix = "_".join(os.path.basename(latest_file).split("_")[:4]) 
            pred_fn = os.path.join(folder, f"{base_prefix}_zPREDICTION.nc")
            
            encoding_dict = {'time': {'units': 'days since 1970-01-01 00:00:00', 'calendar': 'standard'}}
            for v in pred_ds.data_vars:
                encoding_dict[v] = {'zlib': True, 'complevel': 5}
                
            print(f"  Saving predictions to {os.path.basename(pred_fn)}...")
            pred_ds.to_netcdf(pred_fn, encoding=encoding_dict, engine='netcdf4')
            pred_ds.close()
            print("  Done.")
            
        except Exception as e:
            print(f"  Error processing prediction for {var}: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate future predictions")
    parser.add_argument(
        "--mode",
        choices=["daily", "hourly"],
        default="daily",
        help="Pipeline mode: 'daily' uses PIPELINE_CONFIG, 'hourly' uses PIPELINE_CONFIG_HOURLY"
    )
    args = parser.parse_args()
    active_config = PIPELINE_CONFIG_HOURLY if args.mode == "hourly" else PIPELINE_CONFIG
    generate_predictions(active_config, mode=args.mode)
