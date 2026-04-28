import xarray as xr
import numpy as np
import glob
import os

def build_european_mesh_3d():
    scripts_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.dirname(scripts_dir)
    
    raw_path = os.path.join(base_dir, "datasets", "raw_3d")
    output_dir = os.path.join(base_dir, "datasets", "unified_europe_3d")
    os.makedirs(output_dir, exist_ok=True)
    
    # Find all downloaded 3D files
    nc_files = glob.glob(f"{raw_path}/**/*.nc", recursive=True)
    
    if not nc_files:
        print("Error: No 3D NetCDF files found in raw_3d folder.")
        return

    # Horizontal: ~4km for 3D to keep file sizes manageable
    # User requested: -12 to 43 Lon, 29 to 73 Lat
    master_lat = np.arange(29.0, 73.001, 0.04).astype(np.float32)
    master_lon = np.arange(-12.0, 43.001, 0.04).astype(np.float32)
    
    # 1.1 Vertical: Using Med Sea standard levels for high-res vertical profiling accurately covering coastal areas
    # Increased to 40 levels (from 0.5m to ~233m) to provide maximum detail in the photic zone.
    master_depth = np.array([
        1.0182, 3.1653, 5.4649, 7.9209, 10.5366, 13.3159, 16.2625, 19.3804, 22.6732, 26.1448,
        29.7991, 33.6400, 37.6713, 41.8970, 46.3210, 50.9472, 55.7797, 60.8225, 66.0800, 71.5562,
        77.2554, 83.1818, 89.3398, 95.7334, 102.3672, 109.2452, 116.3718, 123.7513, 131.3879, 139.2861,
        147.4503, 155.8850, 164.5947, 173.5836, 182.8564, 192.4170, 202.2699, 212.4182, 222.8687, 233.6267
    ], dtype=np.float32)

    print(f"Targeting 3D Grid (High-Res Vertical): {len(master_lat)} lat x {len(master_lon)} lon x {len(master_depth)} depth levels")

    # 2. Identify the latest common time-slice
    latest_times = []
    for f in nc_files:
        with xr.open_dataset(f) as ds_tmp:
            latest_times.append(ds_tmp.time.values.max())
    
    target_time = max(latest_times)
    print(f"Targeting time slice: {np.datetime_as_string(target_time, unit='D')}")

    processed_layers = []
    # Prioritizing ATL (IBI) for better resolution in the Spanish coast/Vilanova
    region_priority = ["ATL", "MED", "BAL", "BS", "GLO"]

    for region in region_priority:
        f_region = [f for f in nc_files if f"/{region}/" in f]
        if not f_region:
            continue
        
        f = f_region[0]
        print(f"Processing Region (3D): {region}")
        
        with xr.open_dataset(f) as ds:
            # Standardize names
            coord_map = {
                'latitude': 'lat', 'longitude': 'lon', 'depth': 'depth',
                'thetao': 'temp', 'potential_temperature': 'temp'
            }
            ds = ds.rename({k: v for k, v in coord_map.items() if k in ds.coords or k in ds.data_vars})
            
            # Select target time
            if target_time in ds.time.values:
                ds_t = ds.sel(time=target_time)
            else:
                ds_t = ds.isel(time=-1)
            
            # Interpolate to master 3D grid
            print(f"  Interpolating {region} to 3D grid...")
            ds_interp = ds_t[['temp']].interp(
                lat=master_lat, 
                lon=master_lon, 
                depth=master_depth, 
                method="linear"
            )
            
            processed_layers.append(ds_interp.compute())

    # 3. Merge layers by priority
    print("Merging 3D layers...")
    mosaic = processed_layers[0]
    for layer in processed_layers[1:]:
        mosaic = mosaic.combine_first(layer)

    # Add time dimension back
    mosaic = mosaic.expand_dims(time=[target_time])

    # 4. Save
    output_fn = os.path.join(output_dir, "EUROPE_TOTAL_3D_TEMP.nc")
    
    # Ensure attributes
    mosaic.temp.attrs['units'] = 'degree_Celsius'
    mosaic.temp.attrs['long_name'] = 'Potential Temperature'

    print(f"Writing 3D dataset to: {output_fn}")
    mosaic['temp'] = mosaic.temp.astype(np.float32)
    mosaic.to_netcdf(output_fn)
    print(f"Successfully created 3D mesh: {output_fn}")

if __name__ == "__main__":
    build_european_mesh_3d()
