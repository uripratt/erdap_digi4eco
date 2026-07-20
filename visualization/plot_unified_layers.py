import xarray as xr
import matplotlib.pyplot as plt
import os
import numpy as np
import glob
import contextily as ctx

def plot_unified_layers(var_name, config_dict):
    scripts_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.dirname(scripts_dir)
    plots_dir = os.path.join(base_dir, "plots")
    os.makedirs(plots_dir, exist_ok=True)
    
    if var_name not in config_dict:
        print(f"Error: Variable '{var_name}' not found.")
        return

    conf = config_dict[var_name]
    if not conf.get('is_3d', False):
        print(f"Variable '{var_name}' is not 3D. Skipping layers plot.")
        return

    from pipeline.config import DOMAINS
    is_hourly = config_dict[var_name].get("temporal_res") == "PT1H"
    dir_prefix = "unified_europe_hourly_" if is_hourly else "unified_europe_"
    nc_dir = os.path.join(base_dir, "datasets", f"{dir_prefix}{var_name}")
    
    for local_domain in ["OBSEA", "GALWAY", "EUROPE"]:
        if local_domain == "EUROPE":
            nc_files = sorted(glob.glob(os.path.join(nc_dir, f"EUROPE_TOTAL_*_3D_*.nc")))
            title_domain = "Full Europe"
        else:
            nc_files = sorted(glob.glob(os.path.join(nc_dir, f"{local_domain}_LOCAL_*.nc")))
            title_domain = f"{local_domain} DTO"

        if not nc_files:
            print(f"Warning: No 3D NetCDF files found for {var_name} ({local_domain})")
            continue

        latest_file = nc_files[-1]
        print(f"Loading 3D dataset for {local_domain} layers: {latest_file}")
        ds = xr.open_dataset(latest_file)
        
        # Identify Data Array and parameters based on variable
        if var_name == "cur":
            if "speed" not in ds:
                ds["speed"] = np.sqrt(ds["uo"]**2 + ds["vo"]**2)
            da = ds["speed"]
            vmin, vmax = 0.0, 1.5
            cmap = "magma"
            label = "Current Speed (m/s)"
            title_var = "Current Speed"
        elif var_name == "sal":
            da = ds[conf["nc_vars"][0]]
            vmin, vmax = 34.0, 39.0
            cmap = "viridis"
            label = "Salinity (PSU)"
            title_var = "Salinity"
        elif var_name == "temp_3d":
            da = ds[conf["nc_vars"][0]]
            vmin, vmax = 8.0, 24.0
            cmap = "RdYlBu_r"
            label = "Potential Temperature (°C)"
            title_var = "Temperature"
        else:
            da = ds[conf["nc_vars"][0]]
            vmin, vmax = float(da.min()), float(da.max())
            cmap = "viridis"
            label = var_name.upper()
            title_var = var_name.upper()

        # Selection of 9 depths across the whole column (up to ~300m)
        layer_indices = [0, 5, 10, 15, 20, 25, 30, 35, 39]
        bbox = DOMAINS[local_domain]
        extent = [bbox[0], bbox[2], bbox[1], bbox[3]]
        
        fig, axes = plt.subplots(3, 3, figsize=(22, 18), constrained_layout=True)
        axes = axes.flatten()
        
        time_str = np.datetime_as_string(ds.time.values[0], unit='D')
        fig.suptitle(f"3D {title_var} Layers - {title_domain} - {time_str}", 
                     fontsize=26, fontweight='bold')
        
        for i, idx in enumerate(layer_indices):
            print(f"  Plotting {title_var} layer index {idx} ({local_domain})...")
            
            if idx >= len(da.depth):
                print(f"    Warning: Layer index {idx} out of bounds.")
                continue
                
            ds_layer = da.isel(depth=idx, time=0)
            actual_depth = ds_layer.depth.item()
                
            im = ds_layer.plot(
                ax=axes[i], 
                add_colorbar=False, 
                vmin=vmin, 
                vmax=vmax, 
                cmap=cmap,
                shading='auto'
            )
            
            axes[i].set_title(f"Native Layer {idx+1}\nDepth: {actual_depth:.2f} m", fontsize=18, fontweight='bold', color='darkblue')
            axes[i].set_aspect('equal', adjustable='box')
            axes[i].set_xlim(extent[0], extent[1])
            axes[i].set_ylim(extent[2], extent[3])
            axes[i].grid(True, linestyle=':', alpha=0.3)
            
            # Add satellite background (ONLY FOR LOCAL DOMAINS)
            if local_domain != "EUROPE":
                try:
                    ctx.add_basemap(axes[i], source=ctx.providers.Esri.WorldImagery, crs=4326, alpha=0.7)
                except Exception as e:
                    pass

        cbar = fig.colorbar(im, ax=axes, label=label, orientation='vertical', fraction=0.03, pad=0.02)
        cbar.ax.tick_params(labelsize=14)
        
        output_png = os.path.join(plots_dir, f'unified_{var_name}_{local_domain.lower()}_layers_3d.png')
        plt.savefig(output_png, bbox_inches='tight', dpi=150)
        plt.close()
        
        print(f"Interpolated 3x3 Layers collage saved to {output_png}")

if __name__ == "__main__":
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from pipeline.config import PIPELINE_CONFIG
    plot_unified_layers("temp_3d", PIPELINE_CONFIG)
