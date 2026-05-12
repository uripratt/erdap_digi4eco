import xarray as xr
import matplotlib.pyplot as plt
import os
import numpy as np

def plot_obsea_local_dto():
    scripts_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.dirname(scripts_dir)
    nc_path = os.path.join(base_dir, 'datasets', 'unified_europe_3d', 'OBSEA_LOCAL_DTO_3D.nc')
    
    if not os.path.exists(nc_path):
        print(f"Error: Local DTO file not found at {nc_path}")
        return

    print(f"Loading Local DTO: {nc_path}")
    ds = xr.open_dataset(nc_path)
    
    # Plot Surface Layers (Temp & Sal)
    fig, axes = plt.subplots(1, 2, figsize=(20, 8))
    
    # OBSEA Position
    obsea_lon, obsea_lat = 1.7525, 41.182167
    
    # 1. Temperature
    temp_surface = ds.temp.isel(depth=0)
    im1 = temp_surface.plot(
        ax=axes[0],
        cmap='RdYlBu_r',
        add_colorbar=False,
        shading='auto'
    )
    plt.colorbar(im1, ax=axes[0], label="Potential Temperature (°C)")
    axes[0].plot(obsea_lon, obsea_lat, 'r*', markersize=15, label="OBSEA")
    axes[0].set_title("Surface Temperature", fontsize=14, fontweight='bold')
    
    # 2. Salinity
    if 'sal' in ds.data_vars:
        sal_surface = ds.sal.isel(depth=0)
        im2 = sal_surface.plot(
            ax=axes[1],
            cmap='viridis',
            add_colorbar=False,
            shading='auto'
        )
        plt.colorbar(im2, ax=axes[1], label="Salinity (PSU)")
        axes[1].plot(obsea_lon, obsea_lat, 'r*', markersize=15)
        axes[1].set_title("Surface Salinity", fontsize=14, fontweight='bold')
    else:
        axes[1].text(0.5, 0.5, "Salinity data missing", ha='center', va='center')
    
    fig.suptitle(f"OBSEA Local Digital Twin (DTO) - Surface Multi-Variable\nDomain: [1.57, 1.9] Lon, [41.15, 41.26] Lat", 
                 fontsize=18, fontweight='bold')
    
    for ax in axes:
        ax.grid(True, linestyle=':', alpha=0.5)
        ax.set_xlabel("Longitude")
        ax.set_ylabel("Latitude")

    output_png = os.path.join(scripts_dir, 'obsea_local_dto_multivar.png')
    plt.savefig(output_png, bbox_inches='tight', dpi=150)
    plt.close()
    
    print(f"Local DTO multivar plot saved to {output_png}")

if __name__ == "__main__":
    plot_obsea_local_dto()
