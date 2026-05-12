import xarray as xr
import matplotlib.pyplot as plt
import os
import numpy as np

def project_3d_to_2d(lon, lat, depth, angle=30, scale_z=0.02, scale_lat=0.6):
    """Manual isometric-style projection from 3D to 2D."""
    # Convert angle to radians
    rad = np.radians(angle)
    # x_proj = lon - lat * cos(rad)
    # y_proj = lat * sin(rad) - depth * scale_z
    x_proj = lon - (lat - lat.min()) * 0.5
    y_proj = (lat - lat.min()) * scale_lat - depth * scale_z
    return x_proj, y_proj

def plot_obsea_local_dto_3d():
    scripts_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.dirname(scripts_dir)
    nc_path = os.path.join(base_dir, 'datasets', 'unified_europe_3d', 'OBSEA_LOCAL_DTO_3D.nc')
    
    if not os.path.exists(nc_path):
        print(f"Error: Local DTO file not found at {nc_path}")
        return

    print(f"Loading Local DTO: {nc_path}")
    ds = xr.open_dataset(nc_path)
    
    # Metadata
    time_str = np.datetime_as_string(ds.time.values, unit='D')
    
    # Select layers
    # IBI file has ~22 levels in the subset (0-92m)
    layer_indices = [0, 4, 8, 12, 16, 20] 
    
    fig, ax = plt.subplots(figsize=(15, 12))
    ax.set_facecolor('#f0f0f0')
    
    # Coordinates
    lons = ds.lon.values
    lats = ds.lat.values
    LON, LAT = np.meshgrid(lons, lats)
    
    # Color mapping
    norm = plt.Normalize(17, 20)
    cmap = plt.cm.RdYlBu_r
    
    # Plot layers from bottom to top for correct occlusion
    for idx in reversed(layer_indices):
        if idx >= len(ds.depth): continue
        
        depth_val = ds.depth.values[idx]
        temp_layer = ds.temp.isel(depth=idx).values
        
        # Project grid to 2D
        PX, PY = project_3d_to_2d(LON, LAT, depth_val)
        
        # Plot using pcolormesh or scatter
        # pcolormesh needs regular grid, which PX, PY are NOT. 
        # So we use scatter or manual quad plotting.
        # For simplicity and speed, we use scatter with small points
        # or we plot each cell as a small polygon.
        
        # Downsample for speed if needed
        step = 2
        px_ds = PX[::step, ::step]
        py_ds = PY[::step, ::step]
        temp_ds = temp_layer[::step, ::step]
        
        # Flatten and remove NaNs
        mask = ~np.isnan(temp_ds)
        ax.scatter(px_ds[mask], py_ds[mask], c=temp_ds[mask], cmap=cmap, norm=norm, 
                   s=10, alpha=0.6, marker='s')
        
        # Add a depth label
        ax.text(px_ds[0, -1], py_ds[0, -1], f"{depth_val:.1f}m", 
                fontsize=10, fontweight='bold', bbox=dict(facecolor='white', alpha=0.5))

    # Add OBSEA Vertical Line (clipped to actual model bathymetry)
    obsea_lon, obsea_lat = 1.7525, 41.182167
    
    # Extract profile at OBSEA to find bottom depth in model
    profile = ds.temp.sel(lon=obsea_lon, lat=obsea_lat, method='nearest')
    valid_mask = ~np.isnan(profile)
    if valid_mask.any():
        max_depth_idx = np.where(valid_mask)[0][-1]
        actual_bottom = ds.depth.values[max_depth_idx]
        print(f"  Model bathymetry at OBSEA: {actual_bottom:.1f}m")
        
        # Only plot depths within valid range
        p_indices = [i for i in layer_indices if i <= max_depth_idx]
        depth_range = ds.depth.values[p_indices]
        opx, opy = project_3d_to_2d(np.array([obsea_lon]*len(depth_range)), 
                                    np.array([obsea_lat]*len(depth_range)), 
                                    depth_range)
        ax.plot(opx, opy, 'r--', linewidth=2, label=f"OBSEA Profile (to {actual_bottom:.1f}m)")
        ax.scatter(opx[0], opy[0], color='red', s=100, label="OBSEA Surface", zorder=10)
    else:
        print("  Warning: No valid model data at OBSEA coordinates.")

    # Title and Labels
    plt.title(f"3D Waterfall View: OBSEA Local DTO ({time_str})\nStacked Temperature Layers", 
              fontsize=18, fontweight='bold')
    
    # Hide axes as they are projected
    ax.set_xticks([])
    ax.set_yticks([])
    
    # Colorbar
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    cbar = plt.colorbar(sm, ax=ax, orientation='vertical', fraction=0.03, pad=0.04)
    cbar.set_label("Temperature (°C)", fontsize=12, fontweight='bold')
    
    ax.legend()
    
    output_png = os.path.join(scripts_dir, 'obsea_local_dto_3d_pseudo.png')
    plt.savefig(output_png, bbox_inches='tight', dpi=150)
    plt.close()
    
    print(f"Pseudo-3D DTO plot saved to {output_png}")

if __name__ == "__main__":
    plot_obsea_local_dto_3d()
