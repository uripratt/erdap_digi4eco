import xarray as xr
import matplotlib.pyplot as plt
import os
import numpy as np

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

def plot_obsea_profile():
    scripts_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.dirname(scripts_dir)
    nc_path = os.path.join(base_dir, 'datasets', 'unified_europe_3d', 'EUROPE_TOTAL_3D_TEMP.nc')
    
    if not os.path.exists(nc_path):
        nc_path = os.path.join(base_dir, 'datasets', 'unified_3d', 'ocean_temp_3d_vilanova.nc')
        if not os.path.exists(nc_path):
            print(f"Error: 3D file not found.")
            return

    # OBSEA Precise Coordinates
    obsea_lat = 41.182167
    obsea_lon = 1.7525

    print(f"Extracting vertical profile for OBSEA ({obsea_lat}, {obsea_lon})...")
    ds = xr.open_dataset(nc_path)
    
    # Selection (Smart threshold neighbor)
    profile = get_best_profile(ds.temp, obsea_lat, obsea_lon, target_depth=20)
    
    # Filter out NaNs if any (though models usually have data at these coords)
    depths = profile.depth.values
    temps = profile.values
    
    # Plotting
    plt.figure(figsize=(6, 8))
    plt.plot(temps, depths, 'o-', color='tab:red', linewidth=2)
    
    # Invert Y axis to show depth going down
    plt.gca().invert_yaxis()
    
    plt.title(f"OBSEA Vertical Temperature Profile\n{np.datetime_as_string(profile.time.values, unit='D')}")
    plt.xlabel("Temperature (°C)")
    plt.ylabel("Depth (m)")
    plt.grid(True, linestyle='--', alpha=0.6)
    
    # Highlight OBSEA bottom depth (~20m)
    plt.axhline(y=20, color='gray', linestyle=':', label='OBSEA Depth (~20m)')
    plt.legend()

    output_png = os.path.join(scripts_dir, 'obsea_3d_profile.png')
    plt.savefig(output_png, bbox_inches='tight', dpi=150)
    plt.close()
    
    print(f"OBSEA 3D Profile saved to {output_png}")

if __name__ == "__main__":
    plot_obsea_profile()
