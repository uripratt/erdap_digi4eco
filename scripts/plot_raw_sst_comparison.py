import xarray as xr
import matplotlib.pyplot as plt
import numpy as np
import os
import glob

def plot_raw_sst_comparison():
    base_dir = "/home/uripratt/Documents/SARTI/PROJECTS/DEGI4ECO/erddap/erddap_digi4models"
    scripts_dir = os.path.join(base_dir, "scripts")
    
    med_files = glob.glob(os.path.join(base_dir, 'datasets', 'raw_3d', 'MED', '*.nc'))
    ibi_files = glob.glob(os.path.join(base_dir, 'datasets', 'raw_3d', 'ATL', '*.nc'))

    if not med_files or not ibi_files:
        print("Error: Files not found.")
        return

    med_path = sorted(med_files)[-1]
    ibi_path = sorted(ibi_files)[-1]
    
    print(f"Loading MEDSEA: {os.path.basename(med_path)}")
    print(f"Loading IBI: {os.path.basename(ibi_path)}")

    # Domain to plot (OBSEA focus)
    lon_range = (1.57, 1.9)
    lat_range = (41.15, 41.26)
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 8), sharey=True)
    
    # Common colorbar limits
    vmin, vmax = 18.0, 19.0

    # --- MEDSEA Plot ---
    with xr.open_dataset(med_path) as ds_med:
        # Rename coords to standard if needed (MED uses longitude/latitude)
        ds_med = ds_med.rename({'longitude': 'lon', 'latitude': 'lat'})
        # Select domain and surface
        sel_med = ds_med.sel(lon=slice(*lon_range), lat=slice(*lat_range)).isel(depth=0, time=0)
        
        # Plot using pcolormesh (raw cells)
        im1 = ax1.pcolormesh(sel_med.lon, sel_med.lat, sel_med.thetao, 
                            shading='auto', cmap='RdYlBu_r', vmin=vmin, vmax=vmax)
        ax1.set_title(f"MEDSEA Raw Cells (~4.2km)\n{os.path.basename(med_path)[:15]}...", fontsize=12)
        ax1.scatter(1.7525, 41.182167, color='red', marker='*', s=200, label="OBSEA")
        ax1.grid(True, linestyle=':', alpha=0.5)

    # --- IBI Plot ---
    with xr.open_dataset(ibi_path) as ds_ibi:
        ds_ibi = ds_ibi.rename({'longitude': 'lon', 'latitude': 'lat'})
        sel_ibi = ds_ibi.sel(lon=slice(*lon_range), lat=slice(*lat_range)).isel(depth=0, time=0)
        
        im2 = ax2.pcolormesh(sel_ibi.lon, sel_ibi.lat, sel_ibi.thetao, 
                            shading='auto', cmap='RdYlBu_r', vmin=vmin, vmax=vmax)
        ax2.set_title(f"IBI Raw Cells (~2.5km)\n{os.path.basename(ibi_path)[:15]}...", fontsize=12)
        ax2.scatter(1.7525, 41.182167, color='red', marker='*', s=200, label="OBSEA")
        ax2.grid(True, linestyle=':', alpha=0.5)

    # Labels and Colorbar
    for ax in [ax1, ax2]:
        ax.set_xlabel("Longitude")
        ax.legend(loc='upper right')
    ax1.set_ylabel("Latitude")

    fig.subplots_adjust(right=0.85)
    cbar_ax = fig.add_axes([0.88, 0.15, 0.02, 0.7])
    fig.colorbar(im2, cax=cbar_ax, label="Surface Temperature (°C)")

    plt.suptitle(f"Raw Model Resolution Comparison: OBSEA Domain\nNo Interpolation Applied", fontsize=16, fontweight='bold')
    
    output_png = os.path.join(scripts_dir, "obsea_raw_resolution_comparison.png")
    plt.savefig(output_png, bbox_inches='tight', dpi=150)
    plt.close()
    print(f"Raw comparison plot saved to {output_png}")

if __name__ == "__main__":
    plot_raw_sst_comparison()
