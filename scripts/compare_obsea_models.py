import xarray as xr
import matplotlib.pyplot as plt
import os
import numpy as np
import glob

def get_best_profile(ds, lat, lon, target_depth=20, search_radius=0.05):
    """Searches for the nearest valid profile that reaching at least target_depth."""
    lats = ds.latitude.values
    lons = ds.longitude.values
    
    # Selection window
    lat_indices = np.where((lats >= lat - search_radius) & (lats <= lat + search_radius))[0]
    lon_indices = np.where((lons >= lon - search_radius) & (lons <= lon + search_radius))[0]
    
    candidates = []
    
    for i in lat_indices:
        for j in lon_indices:
            p = ds.thetao.isel(latitude=i, longitude=j, time=-1)
            mask = ~np.isnan(p.values)
            if np.any(mask):
                valid_depths = p.depth.values[mask]
                current_max = np.max(valid_depths)
                if current_max >= target_depth:
                    # Calculate distance
                    dist = np.sqrt((ds.latitude.values[i] - lat)**2 + (ds.longitude.values[j] - lon)**2)
                    candidates.append((dist, p))
    
    if candidates:
        # Return candidate with minimum distance
        candidates.sort(key=lambda x: x[0])
        return candidates[0][1]
    
    # Fallback to absolute maximum if no point reaches threshold
    print(f"Warning: No point found within {search_radius} deg reaching {target_depth}m. Falling back to max depth.")
    max_d = -1
    best_p = None
    for i in lat_indices:
        for j in lon_indices:
            p = ds.thetao.isel(latitude=i, longitude=j, time=-1)
            mask = ~np.isnan(p.values)
            if np.any(mask):
                d = p.depth.values[mask].max()
                if d > max_d:
                    max_d = d
                    best_p = p
    return best_p

def compare_models_obsea():
    scripts_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.dirname(scripts_dir)
    
    # OBSEA Precise Coordinates (41º 10,93' N, 001º 45,15' E)
    obsea_lat = 41.182167
    obsea_lon = 1.7525

    # Find the latest files in raw_3d
    med_files = glob.glob(os.path.join(base_dir, 'datasets', 'raw_3d', 'MED', '*.nc'))
    ibi_files = glob.glob(os.path.join(base_dir, 'datasets', 'raw_3d', 'ATL', '*.nc'))

    if not med_files or not ibi_files:
        print("Error: Could not find raw MED or IBI files.")
        return

    med_path = sorted(med_files)[-1]
    ibi_path = sorted(ibi_files)[-1]

    plt.figure(figsize=(8, 10))

    # 1. Process MEDSEA
    print(f"Loading MEDSEA: {os.path.basename(med_path)}")
    with xr.open_dataset(med_path) as ds_med:
        profile_med = get_best_profile(ds_med, obsea_lat, obsea_lon, target_depth=20)
        if profile_med is not None:
            plt.plot(profile_med.values, profile_med.depth.values, 'o-', 
                     label=f'MEDSEA (4.2km) - Max Depth: {profile_med.depth.values[~np.isnan(profile_med.values)].max():.1f}m', 
                     color='tab:blue', linewidth=2)

    # 2. Process IBI (ATL)
    print(f"Loading IBI: {os.path.basename(ibi_path)}")
    with xr.open_dataset(ibi_path) as ds_ibi:
        profile_ibi = get_best_profile(ds_ibi, obsea_lat, obsea_lon, target_depth=20)
        if profile_ibi is not None:
             plt.plot(profile_ibi.values, profile_ibi.depth.values, 's--', 
                      label=f'IBI (2.5km) - Max Depth: {profile_ibi.depth.values[~np.isnan(profile_ibi.values)].max():.1f}m', 
                      color='tab:orange', linewidth=2)

    plt.gca().invert_yaxis()
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.title(f"Model Comparison at OBSEA\n({obsea_lat}N, {obsea_lon}E)")
    plt.xlabel("Temperature (°C)")
    plt.ylabel("Depth (m)")
    plt.legend()
    
    # Highlight OBSEA bottom depth (~20m)
    plt.axhline(y=20, color='gray', linestyle=':', label='OBSEA Depth (~20m)')

    output_png = os.path.join(scripts_dir, 'obsea_model_comparison.png')
    plt.savefig(output_png, bbox_inches='tight', dpi=150)
    plt.close()
    
    print(f"Comparison plot saved to {output_png}")

if __name__ == "__main__":
    compare_models_obsea()
