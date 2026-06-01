import xarray as xr
import numpy as np
import glob
import os
from itertools import groupby


def _get_month_str(t):
    return t.astype('datetime64[s]').item().strftime('%Y%m')


def build_european_mesh(var_name, config_dict, historical=False):
    """
    Builds 2D monthly NetCDF mosaics for a given variable.
    
    For native 2D products (sst, chl, waves): uses conf['res'].
    For 3D products with a surface extraction (temp_3d, sal, cur):
      uses conf['res_surface'] and saves to a separate '_surface' folder.
    """
    if var_name not in config_dict:
        print(f"Error: Variable '{var_name}' not found in configuration.")
        return

    conf = config_dict[var_name]
    is_3d = conf.get('is_3d', False)

    scripts_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.dirname(scripts_dir)

    # Select raw folder and output resolution
    if is_3d:
        # Surface extraction from 3D column data
        folder_name = f"{var_name}_europe_column"
        res = conf.get("res_surface", conf["res"])
        output_var_name = f"{var_name}_surface"
    else:
        folder_name = var_name
        res = conf["res"]
        output_var_name = var_name

    raw_path = os.path.join(base_dir, "datasets", "raw", folder_name)
    output_dir = os.path.join(base_dir, "datasets", f"unified_europe_{output_var_name}")
    os.makedirs(output_dir, exist_ok=True)

    nc_files = glob.glob(f"{raw_path}/**/*.nc", recursive=True)
    if not nc_files:
        print(f"Error: No NetCDF files found in {raw_path}")
        return

    # Europe-wide master grid
    master_lat = np.arange(29.0, 73.0 + res / 2, res).astype(np.float32)
    master_lon = np.arange(-12.0, 43.0 + res / 2, res).astype(np.float32)

    res_label = int(round(res * 100))  # 0.01 → 1, 0.027 → 3, 0.04 → 4
    print(f"Building 2D mesh for '{output_var_name}' at {res}° ({res_label}km equiv.)")

    # Collect all timesteps
    all_times = set()
    for f in nc_files:
        with xr.open_dataset(f) as ds_tmp:
            all_times.update(ds_tmp.time.values)
    all_times = sorted(all_times)
    if not all_times:
        return

    if not historical:
        all_times = [all_times[-1]]
        print(f"NRT Mode: {np.datetime_as_string(all_times[0], unit='D')}")
    else:
        if var_name == 'sst' and len(all_times) > 8:
            all_times = all_times[::5]
            print(f"Historical Mode (Strided for SST): {len(all_times)} timesteps")
        else:
            print(f"Historical Mode: {len(all_times)} timesteps")

    region_priority = conf["priority"]
    grouped = {k: list(v) for k, v in groupby(all_times, key=_get_month_str)}

    loaded_datasets = {}
    for month_str, month_times in grouped.items():
        print(f"\n>>>> Month {month_str} ({len(month_times)} timesteps) <<<<")
        daily_mosaics = []

        def _get_day_str(t):
            return t.astype('datetime64[s]').item().strftime('%Y%m%d')
        day_grouped = {k: list(v) for k, v in groupby(month_times, key=_get_day_str)}

        for day_str, day_times in day_grouped.items():
            daily_mosaics_acc = []
            for target_time in day_times:
                processed_layers = []
    
                for region in region_priority:
                    f_region = [f for f in nc_files if f"/{region}/" in f]
                    if not f_region:
                        continue
    
                    if f_region[0] not in loaded_datasets:
                        ds_orig = xr.open_dataset(f_region[0])
                        coord_map = {'latitude': 'lat', 'longitude': 'lon'}
                        loaded_datasets[f_region[0]] = ds_orig.rename({k: v for k, v in coord_map.items() if k in ds_orig.coords})
    
                    ds = loaded_datasets[f_region[0]]
                    ds_t = ds.sel(time=target_time) if target_time in ds.time.values \
                        else ds.sel(time=target_time, method="nearest")
    
                    vars_to_keep = conf["nc_vars"]
                    ds_t = ds_t[vars_to_keep].drop_vars('time', errors='ignore')
    
                    # Extract surface layer if this is a 3D product
                    if 'depth' in ds_t.coords or 'depth' in ds_t.dims:
                        ds_t = ds_t.isel(depth=0, drop=True)
    
                    # OPTIMIZATION: Clip master grid to dataset bounds to avoid massive empty interpolations
                    ds_lat = ds.lat.values
                    ds_lon = ds.lon.values
                    lat_mask = (master_lat >= ds_lat.min() - res) & (master_lat <= ds_lat.max() + res)
                    lon_mask = (master_lon >= ds_lon.min() - res) & (master_lon <= ds_lon.max() + res)
                    
                    local_lat = master_lat[lat_mask]
                    local_lon = master_lon[lon_mask]
    
                    if len(local_lat) == 0 or len(local_lon) == 0:
                        continue
    
                    # ── Hybrid Interpolation ──
                    ds_linear = ds_t.interp(lat=local_lat, lon=local_lon, method="linear")
                    
                    # Track native data before filling gaps
                    main_var = vars_to_keep[0]
                    native_mask = ds_linear[main_var].notnull()
                    
                    # Fill gaps with nearest neighbor
                    ds_nearest = ds_t.interp(lat=local_lat, lon=local_lon, method="nearest")
                    ds_interp = ds_linear.fillna(ds_nearest)
                    
                    # ── status_mask creation ──
                    st_flag = xr.where(native_mask, 1, 0)
                    st_flag = xr.where((~native_mask) & ds_interp[main_var].notnull(), 2, st_flag)
                    ds_interp["status_mask"] = st_flag.astype(np.int8)
    
                    # Reindex back to master grid (lazy)
                    ds_interp = ds_interp.reindex(lat=master_lat, lon=master_lon)
                    processed_layers.append(ds_interp)
    
                if not processed_layers:
                    continue
    
                # Merge by priority
                mosaic = processed_layers[0]
                for layer in processed_layers[1:]:
                    mosaic = mosaic.combine_first(layer)
                
                # Post-processing (Lazy)
                for v in conf["nc_vars"]:
                    # SST/Temp Kelvin to Celsius check (heuristic without compute)
                    if any(x in v.lower() for x in ["sst", "thetao", "temp"]):
                        # Check attributes or values range
                        if mosaic[v].attrs.get('units') == 'K':
                            mosaic[v] = mosaic[v] - 273.15
                            mosaic[v].attrs['units'] = 'degree_Celsius'
                    
                    mosaic[v] = mosaic[v].astype(np.float32)
    
                if var_name == "cur":
                    uo, vo = conf["nc_vars"]
                    mosaic["speed"] = np.sqrt(mosaic[uo] ** 2 + mosaic[vo] ** 2).astype(np.float32)
                    mosaic["speed"].attrs = {"long_name": "Sea water speed", "units": "m s-1"}

                daily_mosaics_acc.append(mosaic.expand_dims(time=[target_time]))

            if not daily_mosaics_acc:
                continue

            if historical:
                output_fn = os.path.join(
                    output_dir,
                    f"EUROPE_TOTAL_{res_label}KM_{output_var_name}_{day_str}.nc"
                )
                print(f"  Writing Daily: {output_fn}")
                day_ds = xr.concat(daily_mosaics_acc, dim='time')
                day_ds.to_netcdf(output_fn, encoding={'time': {'units': 'days since 1970-01-01 00:00:00', 'calendar': 'standard'}})
                day_ds.close()
                del day_ds
                import gc
                gc.collect()
            else:
                daily_mosaics.extend(daily_mosaics_acc)

        # Clear cache and run GC
        for ds in loaded_datasets.values():
            ds.close()
        loaded_datasets.clear()
        import gc
        gc.collect()

        if historical:
            # Consolidate daily files of this month into a monthly file
            daily_pattern = os.path.join(
                output_dir,
                f"EUROPE_TOTAL_{res_label}KM_{output_var_name}_{month_str}??.nc"
            )
            daily_files = sorted(glob.glob(daily_pattern))
            if daily_files:
                monthly_fn = os.path.join(
                    output_dir,
                    f"EUROPE_TOTAL_{res_label}KM_{output_var_name}_{month_str}.nc"
                )
                print(f"  Consolidating {len(daily_files)} daily files into monthly: {monthly_fn}")
                try:
                    ds = xr.open_mfdataset(daily_files, combine='nested', concat_dim='time', chunks={})
                    encoding_dict = {'time': {'units': 'days since 1970-01-01 00:00:00', 'calendar': 'standard'}}
                    for var in ds.data_vars:
                        encoding_dict[var] = {'zlib': True, 'complevel': 5}
                    ds.to_netcdf(
                        monthly_fn,
                        encoding=encoding_dict,
                        engine='netcdf4'
                    )
                    ds.close()
                    for p in daily_files:
                        os.remove(p)
                    print("  [OK] Saved monthly file and cleaned up daily files.")
                except Exception as e:
                    print(f"  [ERROR] Failed to consolidate month {month_str}: {e}")
        else:
            if daily_mosaics:
                monthly_ds = xr.concat(daily_mosaics, dim='time')
                output_fn = os.path.join(
                    output_dir,
                    f"EUROPE_TOTAL_{res_label}KM_{output_var_name}_{month_str}.nc"
                )
                print(f"  Writing: {output_fn}")
                encoding_dict = {'time': {'units': 'days since 1970-01-01 00:00:00', 'calendar': 'standard'}}
                for var in monthly_ds.data_vars:
                    encoding_dict[var] = {'zlib': True, 'complevel': 5}
                monthly_ds.to_netcdf(output_fn, encoding=encoding_dict, engine='netcdf4')
                monthly_ds.close()


if __name__ == "__main__":
    from pipeline.config import PIPELINE_CONFIG
    build_european_mesh("sst", PIPELINE_CONFIG, historical=False)
