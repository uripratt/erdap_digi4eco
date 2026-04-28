import xarray as xr
import matplotlib.pyplot as plt
import os
import glob
import numpy as np

def plot_raw_comparison():
    base_dir = "/home/uripratt/Documents/SARTI/PROJECTS/DEGI4ECO/erddap/erddap_digi4models"
    
    # 1. Finds raw files
    med_files = glob.glob(os.path.join(base_dir, 'datasets', 'raw_3d', 'MED', '*.nc'))
    ibi_files = glob.glob(os.path.join(base_dir, 'datasets', 'raw_3d', 'ATL', '*.nc'))

    if not med_files or not ibi_files:
        print("Error: Raw files not found.")
        return

    med_path = sorted(med_files)[-1]
    ibi_path = sorted(ibi_files)[-1]

    # Target Domain for both (Unified Domain)
    extent = [-12, 43, 29, 60] # LonMin, LonMax, LatMin, LatMax (Zoned for Europe/Med)

    fig, axes = plt.subplots(1, 2, figsize=(22, 10), constrained_layout=True)

    # Plot MEDSEA Raw
    print("Plotting MEDSEA Raw...")
    with xr.open_dataset(med_path) as ds:
        ds = ds.rename({'latitude': 'lat', 'longitude': 'lon', 'thetao': 'temp'})
        data = ds.temp.isel(time=-1, depth=0)
        im1 = data.plot(ax=axes[0], cmap='RdYlBu_r', add_colorbar=False)
        axes[0].set_xlim(extent[0], extent[1])
        axes[0].set_ylim(extent[2], extent[3])
        axes[0].set_aspect('equal', adjustable='box') # Maintain correct geometry
        axes[0].set_title(f"RAW MEDSEA\nCovers: Med Basin & Black Sea", fontsize=16)
        plt.colorbar(im1, ax=axes[0], label="Temp (°C)", orientation='horizontal', pad=0.05)

    # Plot IBI Raw
    print("Plotting IBI Raw...")
    with xr.open_dataset(ibi_path) as ds:
        ds = ds.rename({'latitude': 'lat', 'longitude': 'lon', 'thetao': 'temp'})
        data = ds.temp.isel(time=-1, depth=0)
        im2 = data.plot(ax=axes[1], cmap='RdYlBu_r', add_colorbar=False)
        axes[1].set_xlim(extent[0], extent[1])
        axes[1].set_ylim(extent[2], extent[3])
        axes[1].set_aspect('equal', adjustable='box')
        axes[1].set_title(f"RAW IBI (Regional)\nCovers: Atlantic & W. Med (Note the WHITE GAPS in the East)", fontsize=16)
        plt.colorbar(im2, ax=axes[1], label="Temp (°C)", orientation='horizontal', pad=0.05)

    plt.suptitle("Hierarchical Composition: Why we merge models?\n(White areas = Missing data in raw files for the European Domain)", fontsize=22)
    
    output_png = os.path.join(base_dir, "scripts", "raw_model_comparison_v2.png")
    plt.savefig(output_png, bbox_inches='tight', dpi=150)
    plt.close()
    print(f"Fixed raw comparison saved to {output_png}")

if __name__ == "__main__":
    plot_raw_comparison()
