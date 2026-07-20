import xarray as xr
import matplotlib.pyplot as plt
import os
import numpy as np
import glob

def get_best_profile(da, lat, lon, target_depth=20, search_radius=0.05):
    """Searches for the nearest valid profile that reaches at least target_depth."""
    lats = da.lat.values
    lons = da.lon.values
    lat_indices = np.where((lats >= lat - search_radius) & (lats <= lat + search_radius))[0]
    lon_indices = np.where((lons >= lon - search_radius) & (lons <= lon + search_radius))[0]
    candidates = []
    for i in lat_indices:
        for j in lon_indices:
            p = da.isel(lat=i, lon=j, time=-1)
            mask = ~np.isnan(p.values)
            if np.any(mask):
                current_max = np.max(p.depth.values[mask])
                if current_max >= target_depth:
                    dist = np.sqrt((lats[i] - lat)**2 + (lons[j] - lon)**2)
                    candidates.append((dist, p))
    if candidates:
        candidates.sort(key=lambda x: x[0])
        return candidates[0][1]
    return da.sel(lat=lat, lon=lon, method='nearest').isel(time=-1)

def plot_unified_profile(var_name, config_dict):
    scripts_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.dirname(scripts_dir)
    plots_dir = os.path.join(base_dir, "plots")
    os.makedirs(plots_dir, exist_ok=True)
    
    if var_name not in config_dict:
        print(f"Error: Variable '{var_name}' not found.")
        return

    conf = config_dict[var_name]
    if not conf.get('is_3d', False):
        print(f"Variable '{var_name}' is not 3D. Skipping profile.")
        return

    is_hourly = config_dict[var_name].get("temporal_res") == "PT1H"
    dir_prefix = "unified_europe_hourly_" if is_hourly else "unified_europe_"
    nc_dir = os.path.join(base_dir, "datasets", f"{dir_prefix}{var_name}")
    nc_files = [f for f in sorted(glob.glob(os.path.join(nc_dir, "OBSEA_LOCAL_*.nc"))) if "PREDICTION" not in f]

    if not nc_files:
        print(f"No 3D NetCDF files found for {var_name} (OBSEA)")
        return

    latest_file = nc_files[-1]
    print(f"Generating 3D Profile for OBSEA using: {latest_file}")
    
    ds = xr.open_dataset(latest_file)

    # OBSEA Precise Coordinates
    obsea_lat = 41.182167
    obsea_lon = 1.7525
    
    # Identify Data Array based on variable
    if var_name == "cur":
        if "speed" not in ds:
            ds["speed"] = np.sqrt(ds["uo"]**2 + ds["vo"]**2)
        da = ds["speed"]
        xlabel = "Speed (m/s)"
        color = "tab:blue"
        title_var = "Current Speed"
    elif var_name == "sal":
        da = ds[conf["nc_vars"][0]]
        xlabel = "Salinity (PSU)"
        color = "tab:green"
        title_var = "Salinity"
    elif var_name == "temp_3d":
        da = ds[conf["nc_vars"][0]]
        xlabel = "Temperature (°C)"
        color = "tab:red"
        title_var = "Temperature"
    else:
        da = ds[conf["nc_vars"][0]]
        xlabel = var_name.upper()
        color = "tab:orange"
        title_var = var_name.upper()

    print(f"  Extracting vertical profile for OBSEA...")
    profile = get_best_profile(da, obsea_lat, obsea_lon, target_depth=20)
    
    depths = profile.depth.values
    vals = profile.values
    
    plt.figure(figsize=(6, 8))
    plt.plot(vals, depths, 'o-', color=color, linewidth=2)
    
    plt.gca().invert_yaxis()
    
    plt.title(f"OBSEA Vertical {title_var} Profile\n{np.datetime_as_string(profile.time.values, unit='D')}")
    plt.xlabel(xlabel)
    plt.ylabel("Depth (m)")
    plt.grid(True, linestyle='--', alpha=0.6)
    
    plt.axhline(y=20, color='gray', linestyle=':', label='OBSEA Depth (~20m)')
    plt.legend()

    output_png = os.path.join(plots_dir, f'unified_{var_name}_obsea_profile.png')
    plt.savefig(output_png, bbox_inches='tight', dpi=150)
    plt.close()
    
    print(f"OBSEA 3D Profile saved to {output_png}")

if __name__ == "__main__":
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from pipeline.config import PIPELINE_CONFIG
    plot_unified_profile("temp_3d", PIPELINE_CONFIG)
