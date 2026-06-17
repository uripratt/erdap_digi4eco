import os
import glob
import re
import xarray as xr

# Base directory setup
base_dir = os.path.dirname(os.path.abspath(__file__))
datasets_dir = os.path.join(base_dir, "datasets")

# Find all 2D variable folders
folder_names = [
    "unified_europe_chl",
    "unified_europe_cur_surface",
    "unified_europe_sal_surface",
    "unified_europe_sst",
    "unified_europe_temp_3d_surface",
    "unified_europe_waves"
]
folders = [os.path.join(datasets_dir, f) for f in folder_names]

print("Starting consolidation of daily NetCDF files into monthly files...")

for folder in folders:
    print(f"\nProcessing folder: {folder}")
    
    # Match daily files ending in _YYYYMMDD.nc (e.g., _20260512.nc)
    daily_files = glob.glob(os.path.join(folder, "*_20[0-9][0-9][0-9][0-9][0-9][0-9].nc"))
    
    if not daily_files:
        print("  No daily files found.")
        continue
        
    # Group daily files by month (YYYYMM)
    monthly_groups = {}
    for f in daily_files:
        basename = os.path.basename(f)
        # Match YYYYMM followed by 2 digits for day
        match = re.search(r'_(\d{6})\d{2}\.nc$', basename)
        if match:
            month = match.group(1)
            monthly_groups.setdefault(month, []).append(f)
            
    for month, paths in monthly_groups.items():
        paths = sorted(paths)
        if not paths:
            continue
            
        # Determine the name of the new monthly file (replace YYYYMMDD with YYYYMM)
        first_file = os.path.basename(paths[0])
        new_basename = re.sub(r'_(\d{8})\.nc$', f'_{month}.nc', first_file)
        monthly_fn = os.path.join(folder, new_basename)
        
        print(f"  -> Consolidating {len(paths)} daily files into monthly: {new_basename}")
        
        try:
            # Open all daily files for this month lazily
            # Inspect first file to see if it has 'depth' dimension
            first_ds = xr.open_dataset(paths[0])
            has_depth = 'depth' in first_ds.dims
            first_ds.close()
            
            chunk_dict = {'time': 1}
            if has_depth:
                chunk_dict['depth'] = 1
                
            # Using combine='by_coords' is safer for preserving time dimensions from single-slice files
            ds = xr.open_mfdataset(paths, combine='by_coords', chunks=chunk_dict)
            
            # Save the consolidated monthly file
            encoding_dict = {'time': {'units': 'days since 1970-01-01 00:00:00', 'calendar': 'standard'}}
            for var in ds.data_vars:
                encoding_dict[var] = {'zlib': True, 'complevel': 5}
                
            ds.to_netcdf(
                monthly_fn, 
                encoding=encoding_dict,
                engine='netcdf4'
            )
            ds.close()
            print("     [OK] Saved monthly file successfully.")
            
            # Delete the daily files to clean up the folder
            for p in paths:
                os.remove(p)
            print("     [OK] Deleted original daily files.")
            
        except Exception as e:
            print(f"     [ERROR] Failed to consolidate month {month}: {e}")

# Trigger ERDDAP force reload
flag_file = os.path.join(base_dir, "conf", "flag", "forceReload")
if os.path.exists(os.path.dirname(flag_file)):
    with open(flag_file, 'w') as f:
        pass
    print("\nTriggered ERDDAP force reload.")

print("\nFinished!")
