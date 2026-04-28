import xarray as xr
import matplotlib.pyplot as plt
import os
import numpy as np

def plot_temperature_layers():
    scripts_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.dirname(scripts_dir)
    nc_path = os.path.join(base_dir, 'datasets', 'unified_europe_3d', 'EUROPE_TOTAL_3D_TEMP.nc')
    
    if not os.path.exists(nc_path):
        print(f"Error: 3D file not found at {nc_path}")
        return

    print(f"Loading 3D dataset: {nc_path}")
    ds = xr.open_dataset(nc_path)
    
    # Selection of 9 native layers (Indices 0, 2, 4, 6, 8, 10, 12, 14, 16)
    layer_indices = [0, 2, 4, 6, 8, 10, 12, 14, 16]
    extent = [-12, 43, 29, 73]
    
    fig, axes = plt.subplots(3, 3, figsize=(22, 18), constrained_layout=True)
    axes = axes.flatten()
    
    time_str = np.datetime_as_string(ds.time.values[0], unit='D')
    fig.suptitle(f"Native Temperature Layers (Raw Model Data) - {time_str}\nFull Domain (-12º to 43º Lon, 29º to 73º Lat)", 
                 fontsize=26, fontweight='bold')
    
    # Consistent scale
    vmin, vmax = 8.0, 24.0
    
    for i, idx in enumerate(layer_indices):
        print(f"  Selecting native layer index: {idx}...")
        
        # RAW NATIVE DATA (No interpolation)
        ds_layer = ds.temp.isel(depth=idx, time=0)
        actual_depth = ds_layer.depth.item()
            
        im = ds_layer.plot(
            ax=axes[i], 
            add_colorbar=False, 
            vmin=vmin, 
            vmax=vmax, 
            cmap='RdYlBu_r', # Scientific Palette
            shading='auto'
        )
        
        axes[i].set_title(f"Native Layer {idx+1}\nDepth: {actual_depth:.2f} m", fontsize=18, fontweight='bold', color='darkblue')
        axes[i].set_aspect('equal', adjustable='box')
        axes[i].set_xlim(extent[0], extent[1])
        axes[i].set_ylim(extent[2], extent[3])
        axes[i].grid(True, linestyle=':', alpha=0.3)
        
        # Add annotation if mostly empty (Med Data Limit)
        if actual_depth > 98:
            axes[i].text(15, 38, "MEDSEA Data Limit\n(No data > 98m in Med Basin)", 
                         color='red', fontsize=10, fontweight='bold', ha='center',
                         bbox=dict(facecolor='white', alpha=0.5))

    # Single colorbar
    cbar = fig.colorbar(im, ax=axes, label="Potential Temperature (°C)", 
                        orientation='vertical', fraction=0.03, pad=0.02)
    cbar.ax.tick_params(labelsize=14)
    
    output_png = os.path.join(scripts_dir, 'temperature_layers_3d_v2.png')
    plt.savefig(output_png, bbox_inches='tight', dpi=150)
    plt.close()
    
    print(f"Interpolated 3x3 Layers collage saved to {output_png}")

if __name__ == "__main__":
    plot_temperature_layers()
