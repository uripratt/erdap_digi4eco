import os
import glob
import xarray as xr
import pandas as pd

base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "datasets")

folders = [
    "unified_europe_sst",
    "unified_europe_chl",
    "unified_europe_waves",
    "unified_europe_sal_surface",
    "unified_europe_cur_surface"
]

print("Checking daily data for April and May 2026...")

for folder in folders:
    print(f"\n--- {folder} ---")
    files = sorted(glob.glob(os.path.join(base_dir, folder, "*.nc")))
    if not files:
        print("  No .nc files found.")
        continue
    
    for f in files:
        filename = os.path.basename(f)
        if "202604" not in filename and "202605" not in filename:
            continue
            
        try:
            ds = xr.open_dataset(f)
            time_len = ds.dims.get('time', 0)
            if time_len > 0:
                times = pd.to_datetime(ds.time.values)
                t_start = times.min()
                t_end = times.max()
                expected_days = 30 if "202604" in filename else 31
                
                # Check frequency
                if len(times) > 1:
                    freq = (times[1] - times[0]).components
                    if freq.days == 1:
                        freq_str = "Daily"
                    elif freq.hours > 0:
                        freq_str = f"Hourly ({freq.hours}h)"
                    else:
                        freq_str = "Sub-hourly or irregular"
                else:
                    freq_str = "N/A (only 1 timestep)"
                
                status = "PASS" if time_len >= expected_days else "FAIL"
                print(f"  {filename}: {status} | {time_len}/{expected_days} days | Freq: {freq_str} | From {t_start.strftime('%Y-%m-%d')} to {t_end.strftime('%Y-%m-%d')}")
            else:
                print(f"  {filename}: FAIL | 0 timesteps")
            ds.close()
        except Exception as e:
            print(f"  {filename}: Error reading - {e}")

print("\nDone.")
