import os
import glob
import xarray as xr
import pandas as pd

base_dir = "/home/uripratt/Documents/SARTI/PROJECTS/DEGI4ECO/erddap/erddap_digi4models/datasets"

folders = [
    "unified_europe_sst",
    "unified_europe_chl",
    "unified_europe_waves",
    "unified_europe_temp_3d_surface",
    "unified_europe_sal_surface",
    "unified_europe_cur_surface"
]

print("Verifying NetCDF time dimensions...")

for folder in folders:
    print(f"\n--- {folder} ---")
    files = sorted(glob.glob(os.path.join(base_dir, folder, "*.nc")))
    if not files:
        print("  No .nc files found.")
        continue
    
    for f in files:
        filename = os.path.basename(f)
        # Check only 202604 and 202605
        if "202604" not in filename and "202605" not in filename:
            continue
            
        try:
            ds = xr.open_dataset(f)
            time_len = ds.dims.get('time', 0)
            if time_len > 0:
                times = pd.to_datetime(ds.time.values)
                t_start = times.min().strftime('%Y-%m-%d %H:%M')
                t_end = times.max().strftime('%Y-%m-%d %H:%M')
                print(f"  {filename}: {time_len} timesteps | From {t_start} to {t_end}")
            else:
                print(f"  {filename}: 0 timesteps")
            ds.close()
        except Exception as e:
            print(f"  {filename}: Error reading - {e}")

print("\nDone.")
