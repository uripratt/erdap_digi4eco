import xarray as xr
import matplotlib.pyplot as plt
import numpy as np
import os

def plot_pseudo_3d_stacked():
    base_dir = "/home/uripratt/Documents/SARTI/PROJECTS/DEGI4ECO/erddap/erddap_digi4models"
    nc_path = os.path.join(base_dir, 'datasets', 'unified_europe_3d', 'EUROPE_TOTAL_3D_TEMP.nc')
    
    if not os.path.exists(nc_path):
        print(f"Error: Unified 3D file not found.")
        return

    print("Loading unified 3D dataset for Pseudo-3D...")
    ds = xr.open_dataset(nc_path)
    
    # Domain: -12 to 43 Lon, 29 to 73 Lat
    # Increasing resolution significantly (subsampling factor of 3 instead of 15)
    ds_sub = ds.isel(lat=slice(None, None, 3), lon=slice(None, None, 3), time=-1)
    
    # Target Depths
    target_depths = [1.0, 5.0, 10.0, 15.0, 20.0, 50.0, 100.0, 150.0, 200.0]
    
    plt.figure(figsize=(22, 16))
    
    # Waterfall parameters
    x_offset = 6.0  # Horizontal shift per layer 
    y_offset = 14.0 # Vertical shift per layer
    
    vmin, vmax = 8.0, 24.0
    
    for i, depth_val in enumerate(target_depths):
        idx = np.abs(ds_sub.depth - depth_val).argmin().item()
        actual_depth = ds_sub.depth.isel(depth=idx).item()
        layer_data = ds_sub.temp.isel(depth=idx).values
        
        # Calculate shifted coordinates
        lons = ds_sub.lon.values + (i * x_offset)
        lats = ds_sub.lat.values + (i * y_offset)
        
        # Plot mesh
        pcm = plt.pcolormesh(lons, lats, layer_data, 
                           cmap='RdYlBu_r', vmin=vmin, vmax=vmax,
                           shading='auto', edgecolors='none', alpha=1.0)
        
        # Label each layer
        plt.text(lons[0]-2, lats[-1]+1, f"DEPTH: {int(actual_depth)}m", 
                 fontweight='bold', fontsize=14, bbox=dict(facecolor='white', alpha=0.7))

    plt.axis('off')
    plt.colorbar(pcm, label="Temperature (°C)", orientation='vertical', fraction=0.03, pad=0.04)
    
    plt.title("Pseudo-3D Temperature Layers: European Domain\n(Surface to 100m - Waterfall Projection)", 
              fontsize=22, pad=20)
    
    output_png = os.path.join(base_dir, "scripts", "europe_3d_waterfall_layers.png")
    plt.savefig(output_png, bbox_inches='tight', dpi=150)
    plt.close()
    print(f"Pseudo-3D Waterfall saved to {output_png}")

if __name__ == "__main__":
    plot_pseudo_3d_stacked()
