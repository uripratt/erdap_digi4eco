import xarray as xr
import numpy as np
import glob
import os

def build_european_mesh():
    scripts_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.dirname(scripts_dir)
    
    raw_path = os.path.join(base_dir, "datasets", "raw")
    output_dir = os.path.join(base_dir, "datasets", "unified_europe_sst")
    os.makedirs(output_dir, exist_ok=True)
    
    # Find all downloaded files
    nc_files = glob.glob(f"{raw_path}/**/*.nc", recursive=True)
    
    if not nc_files:
        print("Error: No NetCDF files found in raw folder.")
        return

    # 1. Define Master Mesh (0.01 degree resolution ~ 1km)
    # Covering expanded domain: -12 to 43 Lon, 29 to 73 Lat
    master_lat = np.arange(29.0, 73.001, 0.01).astype(np.float32)
    master_lon = np.arange(-12.0, 43.001, 0.01).astype(np.float32)

    # 2. Identify the latest common time-slice to save memory
    # We will only process the LATEST day for the plot/initial verification
    all_datasets = []
    # Prioritizing ATL (IBI) for the Spanish coast
    region_priority = ["ATL", "MED", "BAL", "BS", "GLO"]
    
    print("Finding latest time slice across regions...")
    latest_times = []
    for f in nc_files:
        with xr.open_dataset(f) as ds_tmp:
            latest_times.append(ds_tmp.time.values.max())
    
    # Target the absolute latest time available in the catalog
    target_time = max(latest_times)
    print(f"Targeting time slice: {np.datetime_as_string(target_time, unit='D')}")

    processed_layers = []

    for region in region_priority:
        # Find file for this region
        f_region = [f for f in nc_files if f"/{region}/" in f]
        if not f_region:
            continue
        
        f = f_region[0]
        print(f"Processing Region: {region}")
        
        # Load ONLY the target time slice eagerly to avoid dask overhead
        with xr.open_dataset(f) as ds:
            # Standardize names
            coord_map = {'latitude': 'lat', 'longitude': 'lon', 'analysed_sst': 'sst'}
            ds = ds.rename({k: v for k, v in coord_map.items() if k in ds.coords or k in ds.data_vars})
            
            # Select target time (or the closest one if not exact)
            if target_time in ds.time.values:
                ds_t = ds.sel(time=target_time)
            else:
                print(f"  Warning: {region} doesn't have {target_time}, using its latest available.")
                ds_t = ds.isel(time=-1)
            
            # Standardize to 2D
            ds_t = ds_t[['sst']].drop_vars('time', errors='ignore')

            # Interpolate to master grid
            print(f"  Interpolating {region}...")
            ds_interp = ds_t.interp(lat=master_lat, lon=master_lon, method="linear")
            
            # Store in list
            processed_layers.append(ds_interp.compute())

    # 3. Merge layers by priority
    print("Merging layers...")
    mosaic = processed_layers[0]
    for layer in processed_layers[1:]:
        mosaic = mosaic.combine_first(layer)

    # Add time dimension back
    mosaic = mosaic.expand_dims(time=[target_time])

    # 4. Finalize and Save
    output_fn = os.path.join(output_dir, "EUROPE_TOTAL_1KM_SST.nc")
    
    # Check max value for Kelvin conversion
    if float(mosaic.sst.max()) > 100:
        print("Converting Kelvin to Celsius...")
        mosaic['sst'] = mosaic['sst'] - 273.15
        mosaic.sst.attrs['units'] = 'degree_Celsius'
    else:
        mosaic.sst.attrs['units'] = 'degree_Celsius'

    print(f"Writing dataset to: {output_fn}")
    # Write as float32 to save space
    mosaic['sst'] = mosaic.sst.astype(np.float32)
    mosaic.to_netcdf(output_fn)
    print(f"Successfully created: {output_fn}")

if __name__ == "__main__":
    build_european_mesh()
