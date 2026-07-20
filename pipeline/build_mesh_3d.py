import xarray as xr
import numpy as np
import glob
import os
from pipeline.config import DOMAINS
from itertools import groupby


def _get_month_str(t):
    return t.astype('datetime64[s]').item().strftime('%Y%m')


def build_european_mesh_3d(var_name, config_dict, historical=False):
    """
    Builds 3D monthly NetCDF volumes for:
      - EUROPE: 0.05° (~5km) horizontal, 40 native Copernicus depth levels (1m→233m)
      - OBSEA DTO: 0.002° (~200m) horizontal, 50 levels at 1m resolution (1m→50m)
        with high-res bathymetry masking and status_mask provenance variable.
    
    Galway is EXCLUDED (not served from local ERDDAP).
    """
    if var_name not in config_dict:
        print(f"Error: Variable '{var_name}' not found in configuration.")
        return

    conf = config_dict[var_name]
    if not conf.get('is_3d', False):
        print(f"'{var_name}' is not a 3D variable. Skipping.")
        return

    scripts_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.dirname(scripts_dir)

    # ── Depth grids ────────────────────────────────────────────────────────────
    # Native Copernicus levels for Europe (sparse, from model output)
    master_depth_native = np.array([
        1.0182, 3.1653, 5.4649, 7.9209, 10.5366, 13.3159, 16.2625, 19.3804, 22.6732, 26.1448,
        29.7991, 33.6400, 37.6713, 41.8970, 46.3210, 50.9472, 55.7797, 60.8225, 66.0800, 71.5562,
        77.2554, 83.1818, 89.3398, 95.7334, 102.3672, 109.2452, 116.3718, 123.7513, 131.3879, 139.2861,
        147.4503, 155.8850, 164.5947, 173.5836, 182.8564, 192.4170, 202.2699, 212.4182, 222.8687, 233.6267
    ], dtype=np.float32)

    # Ultra-dense levels for OBSEA DTO (1m resolution, 1m→50m)
    master_depth_dto = np.arange(1, 51, 1).astype(np.float32)

    # ── Domain loop (OBSEA + EUROPE only, Galway excluded) ────────────────────
    active_domains = ["OBSEA", "EUROPE"]

    for domain in active_domains:
        print(f"\n>>> Building 3D Mesh for Domain: {domain} <<<")

        # Depth and resolution per domain
        if domain == "EUROPE":
            master_depth = master_depth_native
            res = conf.get("res_europe_3d", 0.05)
            raw_path = os.path.join(base_dir, "datasets", "raw", f"{var_name}_europe_column")
        else:  # OBSEA
            master_depth = master_depth_dto
            res = conf["res"]   # 0.002° = 200m
            raw_path = os.path.join(base_dir, "datasets", "raw", f"{var_name}_{domain.lower()}")

        output_dir = os.path.join(base_dir, "datasets", f"unified_europe_{var_name}")
        os.makedirs(output_dir, exist_ok=True)

        nc_files = glob.glob(f"{raw_path}/**/*.nc", recursive=True)
        if not nc_files:
            print(f"  Warning: No files found in {raw_path}, skipping.")
            continue

        # Build grid for this domain
        bbox = DOMAINS[domain]
        master_lat = np.arange(bbox[1], bbox[3] + res / 2, res).astype(np.float32)
        master_lon = np.arange(bbox[0], bbox[2] + res / 2, res).astype(np.float32)

        res_label = int(round(res * 100))
        print(f"  Grid: {len(master_lat)} lat × {len(master_lon)} lon × {len(master_depth)} depth @ {res}°")

        # Collect all timesteps
        all_times = set()
        for f in nc_files:
            with xr.open_dataset(f) as ds_tmp:
                all_times.update(ds_tmp.time.values)
        all_times = sorted(all_times)
        if not all_times:
            continue

        if not historical:
            cutoff_time = all_times[-1] - np.timedelta64(7, 'D')
            all_times = [t for t in all_times if t >= cutoff_time]
            print(f"  NRT Mode: processing last 7 days window up to {np.datetime_as_string(all_times[-1], unit='D')}")
        else:
            import pandas as pd
            t_start = pd.Timestamp(all_times[0]).normalize()
            t_end = pd.Timestamp(all_times[-1]).normalize() + pd.Timedelta(hours=23, minutes=59, seconds=59)
            
            expected_times = pd.date_range(start=t_start, end=t_end.normalize(), freq='1D').values
            all_times_set = set(all_times)
            for t in expected_times:
                all_times_set.add(t)
                
            all_times = [t for t in all_times_set if t_start <= pd.Timestamp(t) <= t_end]
            all_times = sorted(all_times)
            print(f"  Historical Mode: {len(all_times)} timesteps (dynamically filtered from {t_start.date()} to {t_end.date()}, including empty dates)")
        
        loaded_datasets = {}
        grouped = {k: list(v) for k, v in groupby(all_times, key=_get_month_str)}

        for month_str, month_times in grouped.items():
            print(f"\n  >>>> Month {month_str} ({len(month_times)} timesteps) <<<<")
            daily_mosaics = []

            def _get_day_str(t):
                return t.astype('datetime64[s]').item().strftime('%Y%m%d')
            day_grouped = {k: list(v) for k, v in groupby(month_times, key=_get_day_str)}

            for day_str, day_times in day_grouped.items():
                daily_mosaics_acc = []
                for target_time in day_times:
                    print(f"    Processing: {np.datetime_as_string(target_time, unit='h')}")
                    processed_layers = []
    
                    for region in conf["priority"]:
                        f_region = [f for f in nc_files if f"/{region}/" in f]
                        if not f_region:
                            continue
    
                        if f_region[0] not in loaded_datasets:
                            ds_orig = xr.open_dataset(f_region[0])
                            coord_map = {'latitude': 'lat', 'longitude': 'lon', 'depth': 'depth'}
                            loaded_datasets[f_region[0]] = ds_orig.rename({k: v for k, v in coord_map.items() if k in ds_orig.coords})
    
                        ds = loaded_datasets[f_region[0]]
                        ds_t = ds.sel(time=target_time) if target_time in ds.time.values \
                            else ds.sel(time=target_time, method="nearest")
    
                        vars_to_keep = conf["nc_vars"]
                        ds_t = ds_t[vars_to_keep].drop_vars('time', errors='ignore')
    
                        # OPTIMIZATION: Clip master grid to dataset bounds
                        ds_lat = ds.lat.values
                        ds_lon = ds.lon.values
                        lat_mask = (master_lat >= ds_lat.min() - res) & (master_lat <= ds_lat.max() + res)
                        lon_mask = (master_lon >= ds_lon.min() - res) & (master_lon <= ds_lon.max() + res)
                        
                        local_lat = master_lat[lat_mask]
                        local_lon = master_lon[lon_mask]
    
                        if len(local_lat) == 0 or len(local_lon) == 0:
                            continue
    
                        # Linear interpolation to clipped grid
                        ds_interp = ds_t.interp(
                            lat=local_lat, lon=local_lon, depth=master_depth, method="linear"
                        )
    
                        # ── Provenance tracking (status_mask) ─────────────────
                        main_var = vars_to_keep[0]
                        native_mask = ds_interp[main_var].notnull()
    
                        # Fill coastal gaps with nearest neighbor
                        ds_nearest = ds_t.interp(
                            lat=local_lat, lon=local_lon, depth=master_depth, method="nearest"
                        )
                        ds_interp = ds_interp.fillna(ds_nearest)
    
                        st_flag = xr.where(native_mask, 1, 0)
                        st_flag = xr.where((~native_mask) & ds_interp[main_var].notnull(), 2, st_flag)
                        ds_interp["status_mask"] = st_flag.astype(np.int8)
    
                        # ── Bathymetry masking (OBSEA only) ───────────────────
                        if domain == "OBSEA":
                            bat_path = os.path.join(base_dir, "datasets", "bathymetry", f"{domain}_bathymetry.nc")
                            if os.path.exists(bat_path):
                                with xr.open_dataset(bat_path) as ds_bat:
                                    ds_bat = ds_bat.rename({'latitude': 'lat', 'longitude': 'lon'})
                                    bat_interp = ds_bat["elevation"].interp(lat=local_lat, lon=local_lon, method="linear")
                                    # Efficient 3D masking
                                    depth_da = xr.DataArray(master_depth, dims="depth", coords={"depth": master_depth})
                                    mask_3d = depth_da > -bat_interp
                                    ds_interp = ds_interp.where(~mask_3d)
    
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
                    if var_name == "cur":
                        uo, vo = conf["nc_vars"]
                        mosaic["speed"] = np.sqrt(mosaic[uo] ** 2 + mosaic[vo] ** 2).astype(np.float32)
    
                    for v in conf["nc_vars"]:
                        if "temp" in var_name or "thetao" in var_name:
                            if mosaic[v].attrs.get('units') == 'K':
                                mosaic[v] = mosaic[v] - 273.15
                                mosaic[v].attrs['units'] = 'degree_Celsius'
                        mosaic[v] = mosaic[v].astype(np.float32)

                daily_mosaics_acc.append(mosaic.expand_dims(time=[target_time]))

                if not daily_mosaics_acc:
                    continue

                if historical:
                    date_str = np.datetime_as_string(target_time, unit='D').replace('-', '')
                    prefix = "OBSEA_LOCAL" if domain == "OBSEA" else "EUROPE_TOTAL"
                    output_fn = os.path.join(
                        output_dir,
                        f"{prefix}_{res_label}KM_3D_{var_name}_{day_str}.nc"
                    )
                    print(f"    Saving Daily: {output_fn}")
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

            prefix = "OBSEA_LOCAL" if domain == "OBSEA" else "EUROPE_TOTAL"
            if historical:
                # Consolidate daily files of this month into a monthly file
                daily_pattern = os.path.join(
                    output_dir,
                    f"{prefix}_{res_label}KM_3D_{var_name}_{month_str}??.nc"
                )
                daily_files = sorted(glob.glob(daily_pattern))
                if daily_files:
                    monthly_fn = os.path.join(
                        output_dir,
                        f"{prefix}_{res_label}KM_3D_{var_name}_{month_str}.nc"
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
                    new_ds = xr.concat(daily_mosaics, dim='time')
                    output_fn = os.path.join(
                        output_dir,
                        f"{prefix}_{res_label}KM_3D_{var_name}_{month_str}.nc"
                    )
                    if os.path.exists(output_fn):
                        print(f"  Updating existing monthly file: {output_fn}")
                        try:
                            old_ds = xr.open_dataset(output_fn)
                            monthly_ds = new_ds.combine_first(old_ds)
                            old_ds.close()
                        except Exception as e:
                            print(f"  Warning: Could not open old file ({e}), overwriting.")
                            monthly_ds = new_ds
                    else:
                        print(f"  Writing new monthly file: {output_fn}")
                        monthly_ds = new_ds
                    
                    temp_fn = output_fn + ".tmp"
                    encoding_dict = {'time': {'units': 'days since 1970-01-01 00:00:00', 'calendar': 'standard'}}
                    for var in monthly_ds.data_vars:
                        encoding_dict[var] = {'zlib': True, 'complevel': 5}
                    monthly_ds.to_netcdf(temp_fn, encoding=encoding_dict, engine='netcdf4')
                    monthly_ds.close()
                    os.rename(temp_fn, output_fn)


if __name__ == "__main__":
    from pipeline.config import PIPELINE_CONFIG
    build_european_mesh_3d("temp_3d", PIPELINE_CONFIG, historical=False)
