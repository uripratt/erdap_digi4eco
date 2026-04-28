import xarray as xr
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
import os
import glob

def plot_micro_grids():
    base_dir = "/home/uripratt/Documents/SARTI/PROJECTS/DEGI4ECO/erddap/erddap_digi4models"
    scripts_dir = os.path.join(base_dir, "scripts")
    obsea_lat = 41.182167
    obsea_lon = 1.7525
    
    med_files = glob.glob(os.path.join(base_dir, 'datasets', 'raw_3d', 'MED', '*.nc'))
    ibi_files = glob.glob(os.path.join(base_dir, 'datasets', 'raw_3d', 'ATL', '*.nc'))

    if not med_files or not ibi_files:
        print("Error: Files not found.")
        return

    med_path = sorted(med_files)[-1]
    ibi_path = sorted(ibi_files)[-1]

    plt.figure(figsize=(12, 10))
    ax = plt.gca()

    # Domain for plot: ~10km area around OBSEA
    window = 0.06 
    ax.set_xlim(obsea_lon - window/2, obsea_lon + window/2)
    ax.set_ylim(obsea_lat - window/2, obsea_lat + window/2)

    def draw_grid(path, name, color, alpha=0.3):
        with xr.open_dataset(path) as ds:
            lats = ds.latitude.values
            lons = ds.longitude.values
            
            # Select range
            mask_lat = (lats >= obsea_lat - window) & (lats <= obsea_lat + window)
            mask_lon = (lons >= obsea_lon - window) & (lons <= obsea_lon + window)
            sel_lats = lats[mask_lat]
            sel_lons = lons[mask_lon]
            
            lat_step = np.abs(np.diff(lats[:2])[0])
            lon_step = np.abs(np.diff(lons[:2])[0])

            # Draw cells as patches
            for lat in sel_lats:
                for lon in sel_lons:
                    # Cell bounds
                    rect = patches.Rectangle(
                        (lon - lon_step/2, lat - lat_step/2),
                        lon_step, lat_step,
                        linewidth=1, edgecolor=color, facecolor='none',
                        alpha=alpha, linestyle='--'
                    )
                    ax.add_patch(rect)
            
            # Plot center points
            lon_grid, lat_grid = np.meshgrid(sel_lons, sel_lats)
            ax.scatter(lon_grid.flatten(), lat_grid.flatten(), color=color, s=20, label=f"{name} Grid Center", alpha=0.5)

            # Mark NEAREST to OBSEA
            near_ds = ds.sel(latitude=obsea_lat, longitude=obsea_lon, method='nearest')
            ax.scatter(near_ds.longitude, near_ds.latitude, color=color, s=150, 
                       marker='o', edgecolors='black', label=f"{name} Closest Cell")

    print("Drawing MEDSEA grid...")
    draw_grid(med_path, "MEDSEA", "tab:blue", alpha=0.4)
    print("Drawing IBI grid...")
    draw_grid(ibi_path, "IBI", "tab:orange", alpha=0.4)

    # Plot OBSEA
    ax.scatter(obsea_lon, obsea_lat, color='red', s=300, marker='*', label="OBSEA Position", zorder=10)

    # Add Smart Selection point for IBI (calculated manually/from previous audit)
    # Smart Point: (41.165817, 1.778910)
    ax.scatter(1.778910, 41.165817, color='tab:green', s=200, marker='P', 
               edgecolors='black', label="IBI 'Smart' Selection (20m+ depth)", zorder=11)

    plt.title("Copernicus Model Grids around OBSEA (Vilanova i la Geltrú)\nBlue: MEDSEA (~4.2km) | Orange: IBI (~2.5km)", fontsize=14)
    plt.xlabel("Longitude")
    plt.ylabel("Latitude")
    plt.legend(loc='lower right', frameon=True, framealpha=0.9)
    plt.grid(True, alpha=0.2)

    output_png = os.path.join(base_dir, "scripts", "obsea_grid_map.png")
    plt.savefig(output_png, bbox_inches='tight', dpi=150)
    plt.close()
    print(f"Grid map saved to {output_png}")

if __name__ == "__main__":
    plot_micro_grids()
