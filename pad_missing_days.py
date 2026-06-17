import xarray as xr
import numpy as np
import os
import glob
import pandas as pd

def pad_dataset(var_name, expected_res):
    print(f"=======================================")
    print(f"Padding missing days for {var_name}...")
    base_dir = "/home/uripratt/Documents/SARTI/PROJECTS/DEGI4ECO/erddap/erddap_digi4models/datasets"
    folder = f"unified_europe_{var_name}"
    
    for month_str, days_in_month in [("202604", 30), ("202605", 31)]:
        pattern = f"{base_dir}/{folder}/EUROPE_TOTAL_{expected_res}KM_{var_name}_{month_str}.nc"
        files = glob.glob(pattern)
        if not files:
            print(f"File not found: {pattern}")
            continue
            
        file_path = files[0]
        ds = xr.open_dataset(file_path)
        
        # Determine expected dates
        start_date = f"2026-{month_str[-2:]}-01"
        end_date = f"2026-{month_str[-2:]}-{days_in_month}"
        
        # If waves, pick 12:00:00
        if var_name == "waves":
            expected_times = pd.date_range(start_date, end_date, freq="D") + pd.Timedelta(hours=12)
        else:
            # sst, chl, sal, cur usually at 00:00:00
            expected_times = pd.date_range(start_date, end_date, freq="D")
            
        current_times = pd.DatetimeIndex(ds.time.values)
        
        # For waves, if it's hourly, first resample or just pick nearest to 12:00:00
        if var_name == "waves":
            # Just take the nearest timestep for each day if available
            daily_datasets = []
            for t in expected_times:
                try:
                    # Find closest time in current dataset
                    diffs = np.abs((current_times - t).total_seconds())
                    min_diff_idx = np.argmin(diffs)
                    closest_time = current_times[min_diff_idx]
                    
                    # Get that slice
                    ds_slice = ds.isel(time=[min_diff_idx]).copy()
                    
                    # Update time coordinate
                    ds_slice['time'] = [t]
                    daily_datasets.append(ds_slice)
                except Exception as e:
                    print(f"Error processing {t}: {e}")
                    
            if daily_datasets:
                new_ds = xr.concat(daily_datasets, dim='time')
            else:
                new_ds = ds
        else:
            # For others, reindex with nearest
            new_ds = ds.reindex(time=expected_times, method="nearest")

        # Ensure correct time encoding and save
        out_path = file_path.replace(".nc", "_padded.nc")
        
        encoding_dict = {'time': {'units': 'days since 1970-01-01 00:00:00', 'calendar': 'standard'}}
        for v in new_ds.data_vars:
            encoding_dict[v] = {'zlib': True, 'complevel': 5}
            
        new_ds.to_netcdf(out_path, encoding=encoding_dict, engine='netcdf4')
        ds.close()
        new_ds.close()
        
        # Replace original
        os.replace(out_path, file_path)
        print(f"[{month_str}] {var_name}: padded to {len(expected_times)} timesteps.")

if __name__ == "__main__":
    pad_dataset("sst", 1)
    pad_dataset("chl", 1)
    pad_dataset("waves", 4)
    pad_dataset("sal_surface", 3)
    pad_dataset("cur_surface", 3)
    print("\nSuccessfully padded all 2D datasets to full daily coverage.")
