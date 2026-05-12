import xarray as xr
import numpy as np
import os
import glob

def build_obsea_local_dto(target_date=None):
    scripts_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.dirname(scripts_dir)
    
    raw_path = os.path.join(base_dir, "datasets", "raw_3d", "ATL")
    output_dir = os.path.join(base_dir, "datasets", "unified_europe_3d")
    os.makedirs(output_dir, exist_ok=True)
    
    # OBSEA Local Domain (Requested)
    lon_min, lat_min, lon_max, lat_max = 1.57, 41.15, 1.9, 41.26
    
    # High-Resolution Grid Definition (~200m per cell)
    res = 0.002 
    master_lat = np.arange(lat_min, lat_max + res/2, res).astype(np.float32)
    master_lon = np.arange(lon_min, lon_max + res/2, res).astype(np.float32)
    
    # Find IBI (ATL) file
    nc_files = glob.glob(f"{raw_path}/*.nc")
    if not nc_files:
        print(f"Error: No IBI files found in {raw_path}")
        return
    
    if target_date:
        # Filter by date in filename (e.g. 2026-02-10)
        selected_files = [f for f in nc_files if target_date in f]
        if not selected_files:
            print(f"Error: No IBI file found for date {target_date}")
            return
        ibi_file = selected_files[0]
    else:
        ibi_file = max(nc_files, key=os.path.getctime)
        
    print(f"Generating Local DTO from: {os.path.basename(ibi_file)}")
    
    with xr.open_dataset(ibi_file) as ds:
        # Standardize coordinates
        coord_map = {
            'latitude': 'lat', 'longitude': 'lon', 'depth': 'depth', 
            'thetao': 'temp', 'so': 'sal'
        }
        ds = ds.rename({k: v for k, v in coord_map.items() if k in ds.coords or k in ds.data_vars})
        
        # Select latest time slice
        ds_t = ds.isel(time=-1)
        
        print(f"  Interpolating to Local DTO Grid: {len(master_lat)} lat x {len(master_lon)} lon")
        
        # Variables to include
        vars_to_interp = [v for v in ['temp', 'sal'] if v in ds_t.data_vars]
        
        print(f"  Interpolating to Local DTO Grid: {len(master_lat)} lat x {len(master_lon)} lon (Hybrid Linear/Nearest)")
        
        # 1. Primary: Linear interpolation for smooth gradients
        ds_linear = ds_t[vars_to_interp].interp(
            lat=master_lat,
            lon=master_lon,
            method="linear"
        )
        
        # 2. Secondary: Nearest neighbor to fill gaps at the coast
        ds_nearest = ds_t[vars_to_interp].interp(
            lat=master_lat,
            lon=master_lon,
            method="nearest"
        )
        
        # 3. Combine: Keep smooth gradients, but fill coastal holes
        ds_local = ds_linear.fillna(ds_nearest)
        
        # Add Pressure Approximation (1m ≈ 1 dbar)
        # depth is a coordinate, we want it as a data variable for ERDDAP if needed, 
        # but usually it is just depth. However, user asked for 'pressure'.
        ds_local['pres'] = ds_local['depth'] * 1.01  # Rough conversion to dbar
        ds_local['pres'].attrs['units'] = 'dbar'
        ds_local['pres'].attrs['long_name'] = 'Sea Water Pressure'
        
        # Add metadata
        ds_local.attrs['title'] = "OBSEA Local Digital Twin (DTO) - Multi-Variable"
        ds_local.attrs['domain'] = f"Lon: {lon_min}/{lon_max}, Lat: {lat_min}/{lat_max}"
        ds_local.attrs['resolution'] = f"{res} degrees (~200m)"
        
        output_fn = os.path.join(output_dir, "OBSEA_LOCAL_DTO_3D.nc")
        print(f"Saving Local DTO to: {output_fn}")
        ds_local.to_netcdf(output_fn)
        print("Successfully created Local DTO.")

if __name__ == "__main__":
    import sys
    date_arg = sys.argv[1] if len(sys.argv) > 1 else None
    build_obsea_local_dto(target_date=date_arg)
