import xarray as xr
import os
import numpy as np
import pandas as pd

base_dir = "/home/uripratt/Documents/SARTI/PROJECTS/DEGI4ECO/erddap/erddap_digi4models/datasets"

vars_to_check = {
    "sst": "unified_europe_sst/EUROPE_TOTAL_1KM_sst_202605.nc",
    "chl": "unified_europe_chl/EUROPE_TOTAL_1KM_chl_202605.nc",
    "sal": "unified_europe_sal_surface/EUROPE_TOTAL_3KM_sal_surface_202605.nc"
}

def check_file(v, rel_path):
    fpath = os.path.join(base_dir, rel_path)
    if not os.path.exists(fpath):
        print(f"File {fpath} not found.")
        return
    print(f"\nChecking {v} -> {rel_path}")
    
    try:
        ds = xr.open_dataset(fpath)
        times = pd.to_datetime(ds.time.values)
        print(f"  Total time slices: {len(times)}")
        print(f"  Time range: {times.min()} to {times.max()}")
        
        expected_times = pd.date_range(start="2026-05-01", end="2026-05-31", freq='D')
        
        # Format times slightly to avoid sub-day differences if any
        actual_days = set(times.strftime('%Y-%m-%d'))
        expected_days = set(expected_times.strftime('%Y-%m-%d'))
        
        missing = expected_days - actual_days
        if missing:
            print(f"  Missing days: {sorted(missing)}")
        else:
            print("  No missing days.")
            
        # Check for identical consecutive slices
        data_var = [var for var in ds.data_vars if var not in ['status_mask', 'time']][0]
        print(f"  Using data variable: {data_var} for duplicate check")
        
        identical_pairs = []
        for i in range(1, len(times)):
            t1 = times[i-1]
            t2 = times[i]
            # get values, handle nans
            v1 = ds[data_var].isel(time=i-1).values
            v2 = ds[data_var].isel(time=i).values
            
            # Check if arrays are exactly equal (nan-aware)
            # np.allclose doesn't handle nans well, so:
            mask1 = np.isnan(v1)
            mask2 = np.isnan(v2)
            if np.array_equal(mask1, mask2):
                if np.array_equal(v1[~mask1], v2[~mask2]):
                    identical_pairs.append((t1.strftime('%Y-%m-%d'), t2.strftime('%Y-%m-%d')))
                    
        if identical_pairs:
            print(f"  Found identical consecutive slices: {identical_pairs[:5]} ... (total {len(identical_pairs)})")
        else:
            print("  No identical consecutive slices found.")
            
    except Exception as e:
        print(f"Error checking {v}: {e}")

for v, path in vars_to_check.items():
    check_file(v, path)
