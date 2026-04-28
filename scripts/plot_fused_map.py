import xarray as xr
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
import os
import glob
from PIL import Image

def get_best_profile_info(ds, lat, lon, target_depth=20, search_radius=0.05):
    """Searches for the nearest valid profile that reaching at least target_depth."""
    lats = ds.latitude.values
    lons = ds.longitude.values
    lat_indices = np.where((lats >= lat - search_radius) & (lats <= lat + search_radius))[0]
    lon_indices = np.where((lons >= lon - search_radius) & (lons <= lon + search_radius))[0]
    candidates = []
    for i in lat_indices:
        for j in lon_indices:
            p = ds.thetao.isel(latitude=i, longitude=j, time=-1)
            mask = ~np.isnan(p.values)
            if np.any(mask):
                current_max = np.max(p.depth.values[mask])
                if current_max >= target_depth:
                    dist = np.sqrt((ds.latitude.values[i] - lat)**2 + (ds.longitude.values[j] - lon)**2)
                    candidates.append((dist, float(ds.latitude.values[i]), float(ds.longitude.values[j])))
    if candidates:
        candidates.sort(key=lambda x: x[0])
        return candidates[0][1], candidates[0][2] # lat, lon
    return None, None

def plot_fused_map():
    base_dir = "/home/uripratt/Documents/SARTI/PROJECTS/DEGI4ECO/erddap/erddap_digi4models"
    scripts_dir = os.path.join(base_dir, "scripts")
    
    # OBSEA Precise Coordinates
    obsea_lat = 41.182167
    obsea_lon = 1.7525
    
    # Satellite Image Info
    sat_img_path = os.path.join(scripts_dir, "obsea_satellite_esri.jpg")
    sat_extent = [1.70, 1.85, 41.15, 41.22] 

    if not os.path.exists(sat_img_path):
        print(f"Error: Satellite image not found at {sat_img_path}")
        return

    med_files = glob.glob(os.path.join(base_dir, 'datasets', 'raw_3d', 'MED', '*.nc'))
    ibi_files = glob.glob(os.path.join(base_dir, 'datasets', 'raw_3d', 'ATL', '*.nc'))

    if not med_files or not ibi_files:
        print("Error: Model files not found.")
        return

    med_path = sorted(med_files)[-1]
    ibi_path = sorted(ibi_files)[-1]

    plt.figure(figsize=(15, 12))
    ax = plt.gca()

    # 1. Load and display satellite image
    img = Image.open(sat_img_path)
    ax.imshow(img, extent=sat_extent, alpha=0.9)

    # 2. Draw grids
    def draw_grid(path, name, color, alpha_rect=0.2):
        with xr.open_dataset(path) as ds:
            lats = ds.latitude.values
            lons = ds.longitude.values
            
            mask_lat = (lats >= sat_extent[2]) & (lats <= sat_extent[3])
            mask_lon = (lons >= sat_extent[0]) & (lons <= sat_extent[1])
            sel_lats = lats[mask_lat]
            sel_lons = lons[mask_lon]
            
            lat_step = np.abs(np.diff(lats[:2])[0])
            lon_step = np.abs(np.diff(lons[:2])[0])

            # Draw cells
            for lat in sel_lats:
                for lon in sel_lons:
                    rect = patches.Rectangle(
                        (lon - lon_step/2, lat - lat_step/2),
                        lon_step, lat_step,
                        linewidth=1.5, edgecolor=color, facecolor='none',
                        alpha=0.6, linestyle='-'
                    )
                    ax.add_patch(rect)
            
            # Plot center points
            lon_grid, lat_grid = np.meshgrid(sel_lons, sel_lats)
            ax.scatter(lon_grid.flatten(), lat_grid.flatten(), color=color, s=25, 
                       marker='+', label=f"{name} Grid Center", alpha=0.8)

            # Mark NEAREST to OBSEA
            near_ds = ds.sel(latitude=obsea_lat, longitude=obsea_lon, method='nearest')
            ax.scatter(near_ds.longitude, near_ds.latitude, color=color, s=200, 
                       marker='o', edgecolors='white', linewidth=2, label=f"{name} Closest Cell")

    print("Overlaying MEDSEA grid...")
    draw_grid(med_path, "MEDSEA", "cyan")
    print("Overlaying IBI grid...")
    draw_grid(ibi_path, "IBI", "orange")

    # 3. Mark OBSEA and Best Selection
    ax.scatter(obsea_lon, obsea_lat, color='red', s=400, marker='*', 
               edgecolors='white', linewidth=2, label="OBSEA Position", zorder=10)
    
    # Get NEW Best Selection for IBI (Threshold 20m)
    with xr.open_dataset(ibi_path) as ds_ibi:
        best_lat, best_lon = get_best_profile_info(ds_ibi, obsea_lat, obsea_lon, target_depth=20)
        if best_lat is not None:
            ax.scatter(best_lon, best_lat, color='lime', s=250, marker='P', 
                       edgecolors='black', label="IBI Best Selection (Nearest >= 20m)", zorder=11)

    ax.set_xlim(sat_extent[0], sat_extent[1])
    ax.set_ylim(sat_extent[2], sat_extent[3])
    
    plt.title("Fused Map: Satellite Orthophoto + Copernicus Model Grids\nFine Grid (Orange): IBI (2.5km) | Coarse Grid (Cyan): MEDSEA (4.2km)", 
              fontsize=16, pad=20)
    plt.xlabel("Longitude", fontsize=12)
    plt.ylabel("Latitude", fontsize=12)
    plt.legend(loc='upper right', frameon=True, framealpha=0.8, fontsize=10)
    
    output_png = os.path.join(base_dir, "scripts", "obsea_fused_map.png")
    plt.savefig(output_png, bbox_inches='tight', dpi=200)
    plt.close()
    print(f"Fused map saved to {output_png}")

if __name__ == "__main__":
    plot_fused_map()
