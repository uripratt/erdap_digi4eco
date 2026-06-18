import xarray as xr
import numpy as np
import glob
import os
import pandas as pd
from itertools import groupby
from pipeline.config import MY_CUTOFF


def _get_month_str(t):
    return t.astype('datetime64[s]').item().strftime('%Y%m')


def _get_nc_vars_for_region(conf, region):
    """
    Resolves nc_vars for a given region.
      - nc_vars is a list  → uniform (P1D mode, or any uniform-source variable)
      - nc_vars is a dict  → per-region mapping (PT1H SST mixes satellite + model)
    """
    nc_vars_def = conf["nc_vars"]
    if isinstance(nc_vars_def, dict):
        return nc_vars_def.get(region, conf.get("nc_vars_default", list(nc_vars_def.values())[0]))
    return nc_vars_def


def _get_canonical_nc_vars(conf):
    """
    Returns the union of all variable names used across regions.
    For a list, returns it directly. For a dict, returns the sorted union.
    This is used for allocating the empty NaN mosaic and post-processing.
    """
    nc_vars_def = conf["nc_vars"]
    if isinstance(nc_vars_def, dict):
        return sorted(set(v for vlist in nc_vars_def.values() for v in vlist))
    return nc_vars_def


def _forward_fill_daily_to_hourly(ds_daily, target_hours):
    """
    Given a dataset with daily timesteps, forward-fills each day's value to
    all hourly slots within that day. Used for CHL in hourly mode.
    """
    # Build a full hourly DatetimeIndex
    hourly_times = pd.date_range(
        start=pd.Timestamp(ds_daily.time.values[0]).normalize(),
        end=pd.Timestamp(ds_daily.time.values[-1]).normalize() + pd.Timedelta(hours=23),
        freq="1h"
    )
    # Filter to only the hours actually requested
    hourly_times = hourly_times[hourly_times.isin(target_hours)]
    if len(hourly_times) == 0:
        return None

    # Reindex daily → hourly with forward-fill
    ds_hourly = ds_daily.reindex(time=hourly_times, method="ffill")
    return ds_hourly


def build_european_mesh(var_name, config_dict, historical=False):
    """
    Builds 2D monthly NetCDF mosaics for a given variable.

    Supports two pipeline modes via the 'temporal_res' field in config:
      - P1D (daily):  one timestep per day; output to unified_europe_{var}
      - PT1H (hourly): one timestep per hour; output to unified_europe_hourly_{var}
        * CHL has no hourly product → the daily mosaic is forward-filled to PT1H.
        * SST uses a dict of nc_vars per region (satellite + model mixed sources);
          the output variable is renamed to 'analysed_sst' for ERDDAP consistency.

    For native 2D products (sst, chl, waves): uses conf['res'].
    For 3D products with a surface extraction (temp_3d, sal, cur):
      uses conf['res_surface'] and saves to a separate '_surface' folder.
    """
    if var_name not in config_dict:
        print(f"Error: Variable '{var_name}' not found in configuration.")
        return

    conf = config_dict[var_name]
    is_3d = conf.get('is_3d', False)
    temporal_res = conf.get('temporal_res', 'P1D')
    is_hourly = temporal_res.startswith('PT')
    # CHL in hourly mode: download is daily, output is hourly via forward-fill
    source_temporal_res = conf.get('source_temporal_res', temporal_res)
    chl_ffill = (is_hourly and source_temporal_res == 'P1D')

    scripts_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.dirname(scripts_dir)

    # Select raw folder and output resolution
    if is_3d:
        folder_name = f"{var_name}_europe_column"
        res = conf.get("res_surface", conf["res"])
        output_var_name = f"{var_name}_surface"
    else:
        folder_name = var_name
        res = conf["res"]
        output_var_name = var_name

    # Hourly outputs go to a separate folder to avoid colliding with daily files
    if is_hourly:
        output_dir = os.path.join(base_dir, "datasets", f"unified_europe_hourly_{output_var_name}")
    else:
        output_dir = os.path.join(base_dir, "datasets", f"unified_europe_{output_var_name}")
    os.makedirs(output_dir, exist_ok=True)

    raw_path = os.path.join(base_dir, "datasets", "raw", folder_name)
    nc_files = glob.glob(f"{raw_path}/**/*.nc", recursive=True)
    if not nc_files:
        print(f"Error: No NetCDF files found in {raw_path}")
        return

    # The canonical set of variable names for mosaic allocation and post-processing.
    # For SST in hourly mode nc_vars is a dict; canonical output will be normalised below.
    canonical_vars = _get_canonical_nc_vars(conf)

    # Europe-wide master grid
    master_lat = np.arange(29.0, 73.0 + res / 2, res).astype(np.float32)
    master_lon = np.arange(-12.0, 43.0 + res / 2, res).astype(np.float32)

    res_label = int(round(res * 100))  # 0.01 → 1, 0.027 → 3, 0.04 → 4
    print(f"Building 2D mesh for '{output_var_name}' | res={res}° | temporal_res={temporal_res}")

    # ── Collect all timesteps across raw files ────────────────────────────────
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
        t_start = pd.Timestamp("2026-04-01")
        t_end = pd.Timestamp("2026-05-31T23:59:59")
        all_times = [t for t in all_times if t_start <= pd.Timestamp(t) <= t_end]
        print(f"Historical Mode: {len(all_times)} timesteps (filtered for Apr-May 2026)")

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

            # ── CHL forward-fill: build daily mosaic first, then expand to hours ──
            if chl_ffill:
                # day_times contains one daily timestep; build the daily mosaic
                # then replicate it for each hour of that day
                target_time = day_times[0]
                hour_range = pd.date_range(
                    start=pd.Timestamp(target_time.astype('datetime64[s]').item()).normalize(),
                    periods=24, freq="1h"
                )
                day_times_to_build = [target_time]  # build mosaic once, expand after
            else:
                hour_range = None
                day_times_to_build = day_times

            for target_time in day_times_to_build:
                processed_layers = []

                for region in region_priority:
                    f_region = [f for f in nc_files if f"/{region}/" in f]
                    if not f_region:
                        continue

                    if f_region[0] not in loaded_datasets:
                        ds_orig = xr.open_dataset(f_region[0])
                        coord_map = {'latitude': 'lat', 'longitude': 'lon'}
                        loaded_datasets[f_region[0]] = ds_orig.rename(
                            {k: v for k, v in coord_map.items() if k in ds_orig.coords}
                        )

                    ds = loaded_datasets[f_region[0]]
                    if target_time in ds.time.values:
                        ds_t = ds.sel(time=target_time)
                    else:
                        # No data for this timestep in this region → leave as NaN
                        continue

                    # Resolve the correct variables for this region
                    vars_to_keep = _get_nc_vars_for_region(conf, region)

                    # Keep only the variables that actually exist in this dataset
                    available = [v for v in vars_to_keep if v in ds_t.data_vars]
                    if not available:
                        print(f"  Warning: vars {vars_to_keep} not found in {region} dataset. Skipping.")
                        continue
                    ds_t = ds_t[available].drop_vars('time', errors='ignore')

                    # Extract surface layer if this is a 3D product
                    if 'depth' in ds_t.coords or 'depth' in ds_t.dims:
                        ds_t = ds_t.isel(depth=0, drop=True)

                    # OPTIMIZATION: Clip master grid to dataset bounds
                    ds_lat = ds.lat.values
                    ds_lon = ds.lon.values
                    lat_mask = (master_lat >= ds_lat.min() - res) & (master_lat <= ds_lat.max() + res)
                    lon_mask = (master_lon >= ds_lon.min() - res) & (master_lon <= ds_lon.max() + res)

                    local_lat = master_lat[lat_mask]
                    local_lon = master_lon[lon_mask]

                    if len(local_lat) == 0 or len(local_lon) == 0:
                        continue

                    # ── Hybrid Interpolation ──────────────────────────────────
                    ds_linear = ds_t.interp(lat=local_lat, lon=local_lon, method="linear")

                    main_var = available[0]
                    native_mask = ds_linear[main_var].notnull()

                    ds_nearest = ds_t.interp(lat=local_lat, lon=local_lon, method="nearest")
                    ds_interp = ds_linear.fillna(ds_nearest)

                    # ── status_mask ───────────────────────────────────────────
                    st_flag = xr.where(native_mask, 1, 0)
                    st_flag = xr.where((~native_mask) & ds_interp[main_var].notnull(), 2, st_flag)
                    ds_interp["status_mask"] = st_flag.astype(np.int8)

                    # ── data_type: 0=MY validated, 1=NRT, 2=Prediction ────────
                    ts = pd.Timestamp(target_time.astype('datetime64[s]').item())
                    if not historical:
                        dtype_val = np.int8(1)  # NRT mode
                    else:
                        dtype_val = np.int8(0) if ts < pd.Timestamp(MY_CUTOFF) else np.int8(1)
                    ds_interp["data_type"] = xr.full_like(st_flag, dtype_val, dtype=np.int8)

                    # Reindex back to master grid
                    ds_interp = ds_interp.reindex(lat=master_lat, lon=master_lon)
                    processed_layers.append((region, ds_interp))

                if not processed_layers:
                    empty_mosaic = xr.Dataset(coords={'lat': master_lat, 'lon': master_lon})
                    for v in canonical_vars:
                        empty_mosaic[v] = xr.DataArray(
                            np.nan, coords=[master_lat, master_lon], dims=['lat', 'lon'], name=v
                        )
                    empty_mosaic["status_mask"] = xr.DataArray(
                        0, coords=[master_lat, master_lon], dims=['lat', 'lon']
                    ).astype(np.int8)
                    ts_empty = pd.Timestamp(target_time.astype('datetime64[s]').item())
                    dtype_empty = np.int8(0) if (historical and ts_empty < pd.Timestamp(MY_CUTOFF)) else np.int8(1)
                    empty_mosaic["data_type"] = xr.DataArray(
                        dtype_empty, coords=[master_lat, master_lon], dims=['lat', 'lon']
                    ).astype(np.int8)
                    processed_layers = [("__empty__", empty_mosaic)]

                # Merge layers by priority
                # When nc_vars is a dict per region, each layer may have different
                # variable names (e.g., thetao vs sea_surface_subskin_temperature).
                # We normalise heterogeneous SST layers to a single canonical name
                # ('analysed_sst') before merging.
                nc_vars_def = conf["nc_vars"]
                is_heterogeneous = isinstance(nc_vars_def, dict)

                if is_heterogeneous:
                    # Determine canonical output variable name (use first nc_vars_default)
                    canonical_out_var = conf.get("nc_vars_default", ["analysed_sst"])[0]

                layers_normalised = []
                for region_label, layer in processed_layers:
                    if is_heterogeneous:
                        # Rename whatever source variable exists to the canonical name.
                        # e.g.: thetao → analysed_sst,  sea_surface_subskin_temperature → analysed_sst
                        rename_map = {}
                        for v in list(layer.data_vars):
                            if v not in ("status_mask", "prediction_flag") and v != canonical_out_var:
                                rename_map[v] = canonical_out_var
                        if rename_map:
                            # If the canonical name already exists as another variable in the
                            # same layer (e.g. GLO model ships both thetao AND analysed_sst),
                            # drop the duplicate before renaming to avoid xarray conflict.
                            if canonical_out_var in layer.data_vars:
                                layer = layer.drop_vars(canonical_out_var)
                            layer = layer.rename(rename_map)
                    layers_normalised.append(layer)

                mosaic = layers_normalised[0]
                for layer in layers_normalised[1:]:
                    mosaic = mosaic.combine_first(layer)

                # ── Post-processing ───────────────────────────────────────────
                # Use canonical_vars or the normalised output var list
                out_vars = [canonical_out_var] if is_heterogeneous else canonical_vars
                for v in out_vars:
                    if v not in mosaic.data_vars:
                        continue
                    # Kelvin → Celsius
                    if any(x in v.lower() for x in ["sst", "thetao", "temp", "subskin"]):
                        units_attr = mosaic[v].attrs.get('units', '')
                        if units_attr == 'K' or units_attr.lower() == 'kelvin':
                            mosaic[v] = mosaic[v] - 273.15
                            mosaic[v].attrs['units'] = 'degree_Celsius'
                    mosaic[v] = mosaic[v].astype(np.float32)

                if var_name == "cur":
                    uo, vo = canonical_vars[0], canonical_vars[1]
                    if uo in mosaic.data_vars and vo in mosaic.data_vars:
                        mosaic["speed"] = np.sqrt(mosaic[uo] ** 2 + mosaic[vo] ** 2).astype(np.float32)
                        mosaic["speed"].attrs = {"long_name": "Sea water speed", "units": "m s-1"}

                # ── Expand to hourly timesteps if CHL forward-fill ────────────
                if chl_ffill and hour_range is not None:
                    for h in hour_range:
                        daily_mosaics_acc.append(mosaic.expand_dims(time=[h.to_datetime64()]))
                else:
                    daily_mosaics_acc.append(mosaic.expand_dims(time=[target_time]))

            if not daily_mosaics_acc:
                continue

            if historical:
                output_fn = os.path.join(
                    output_dir,
                    f"EUROPE_TOTAL_{res_label}KM_{temporal_res}_{output_var_name}_{day_str}.nc"
                )
                print(f"  Writing Daily: {output_fn}")
                day_ds = xr.concat(daily_mosaics_acc, dim='time')
                day_ds.to_netcdf(
                    output_fn,
                    encoding={'time': {'units': 'hours since 1970-01-01 00:00:00', 'calendar': 'standard'}}
                )
                day_ds.close()
                del day_ds
                import gc
                gc.collect()
            else:
                daily_mosaics.extend(daily_mosaics_acc)

        # Clear dataset cache
        for ds in loaded_datasets.values():
            ds.close()
        loaded_datasets.clear()
        import gc
        gc.collect()

        if historical:
            # Consolidate daily files of this month into a monthly file
            daily_pattern = os.path.join(
                output_dir,
                f"EUROPE_TOTAL_{res_label}KM_{temporal_res}_{output_var_name}_{month_str}??.nc"
            )
            daily_files = sorted(glob.glob(daily_pattern))
            if daily_files:
                monthly_fn = os.path.join(
                    output_dir,
                    f"EUROPE_TOTAL_{res_label}KM_{temporal_res}_{output_var_name}_{month_str}.nc"
                )
                print(f"  Consolidating {len(daily_files)} daily files into monthly: {monthly_fn}")
                try:
                    ds = xr.open_mfdataset(daily_files, combine='by_coords', chunks={})
                    time_units = 'hours since 1970-01-01 00:00:00' if is_hourly else 'days since 1970-01-01 00:00:00'
                    encoding_dict = {'time': {'units': time_units, 'calendar': 'standard'}}
                    for var in ds.data_vars:
                        encoding_dict[var] = {'zlib': True, 'complevel': 5}
                    ds.to_netcdf(monthly_fn, encoding=encoding_dict, engine='netcdf4')
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
                    f"EUROPE_TOTAL_{res_label}KM_{temporal_res}_{output_var_name}_{month_str}.nc"
                )
                print(f"  Writing: {output_fn}")
                time_units = 'hours since 1970-01-01 00:00:00' if is_hourly else 'days since 1970-01-01 00:00:00'
                encoding_dict = {'time': {'units': time_units, 'calendar': 'standard'}}
                for var in monthly_ds.data_vars:
                    encoding_dict[var] = {'zlib': True, 'complevel': 5}
                monthly_ds.to_netcdf(output_fn, encoding=encoding_dict, engine='netcdf4')
                monthly_ds.close()


if __name__ == "__main__":
    from pipeline.config import PIPELINE_CONFIG
    build_european_mesh("sst", PIPELINE_CONFIG, historical=False)
