import xarray as xr
import matplotlib.pyplot as plt
import numpy as np
import os
import glob
import contextily as ctx
from pipeline.config import DOMAINS

def _generate_map(data_slice, var_name, conf, domain_name, plots_dir, time_str, ds_bat=None):
    fig, ax = plt.subplots(figsize=(14, 10), dpi=150)
    
    # Scientific color palettes and standardized ranges
    style_config = {
        "sst": {"cmap": "magma", "label": "Temperature (°C)", "range": (12, 28)},
        "chl": {"cmap": "YlGn", "label": "Chlorophyll-a (mg/m³)", "range": (0.01, 1.5)},
        "sal": {"cmap": "viridis", "label": "Salinity (PSU)", "range": (36, 39)},
        "temp_3d": {"cmap": "magma", "label": "Temperature (°C)", "range": (12, 28)},
        "cur": {"cmap": "plasma", "label": "Current Speed (m/s)", "range": (0, 0.4)},
        "waves": {"cmap": "YlGnBu", "label": "Significant Wave Height (m)", "range": (0, 4)}
    }
    
    style = style_config.get(var_name, {"cmap": "viridis", "label": var_name, "range": (None, None)})
    vmin, vmax = style["range"]
    
    # ------------------
    # DATA PREPARATION
    # ------------------
    if var_name == 'cur':
        u, v = data_slice["uo"], data_slice["vo"]
        data_to_plot = np.sqrt(u**2 + v**2)
    elif var_name == 'waves':
        data_to_plot = data_slice["VHM0"]
    else:
        da = data_slice[conf["nc_vars"][0]]
        data_to_plot = da - 273.15 if da.max() > 100 else da

    # ------------------
    # PLOTTING
    # ------------------
    im = ax.pcolormesh(data_to_plot.lon, data_to_plot.lat, data_to_plot.values, 
                       cmap=style["cmap"], vmin=vmin, vmax=vmax, shading='auto', alpha=0.85)
    plt.colorbar(im, ax=ax, label=style["label"])
    
    # Vectors for Currents/Waves
    if var_name == 'cur':
        step_deg = 0.05 if domain_name != "europe" else 0.5
        step = max(1, int(step_deg / conf['res']))
        u_p = data_slice["uo"].isel(lat=slice(None, None, step), lon=slice(None, None, step))
        v_p = data_slice["vo"].isel(lat=slice(None, None, step), lon=slice(None, None, step))
        ax.quiver(u_p.lon, u_p.lat, u_p.values, v_p.values, scale=10, color='white', alpha=0.8)
    
    # ------------------
    # SCIENTIFIC OVERLAYS
    # ------------------
    # Bathymetry Contours
    if ds_bat is not None:
        levels = sorted([-20, -50, -100, -200, -500, -1000])
        cs = ax.contour(ds_bat.lon, ds_bat.lat, ds_bat.elevation, levels=levels, 
                        colors='white', linewidths=0.6, alpha=0.5)
        ax.clabel(cs, inline=True, fontsize=8, fmt='%d m')

    # Basemap
    if domain_name.lower() in ["obsea", "galway"]:
        try:
            ctx.add_basemap(ax, source=ctx.providers.Esri.WorldImagery, crs=4326, alpha=0.4)
        except: pass

    ax.set_xlabel("Longitude (°E)")
    ax.set_ylabel("Latitude (°N)")
    ax.set_title(f"DEGI4ECO Digital Twin: {domain_name.upper()} {var_name.upper()}\nTime: {time_str}", 
                 fontsize=15, fontweight='bold', pad=15)
    ax.grid(True, linestyle=':', alpha=0.5)

    output_png = os.path.join(plots_dir, f'unified_{var_name}_{domain_name}_map.png')
    plt.tight_layout()
    plt.savefig(output_png, bbox_inches='tight', dpi=200)
    plt.close()
    print(f"Plot saved to {output_png}")

def plot_unified_maps(var_name, config_dict):
    scripts_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.dirname(scripts_dir)
    plots_dir = os.path.join(base_dir, "plots")
    os.makedirs(plots_dir, exist_ok=True)

    conf = config_dict[var_name]
    nc_dir = os.path.join(base_dir, "datasets", f"unified_europe_{var_name}")
    nc_files = sorted(glob.glob(os.path.join(nc_dir, "*.nc")))
    if not nc_files: return

    latest_file = nc_files[-1]
    ds = xr.open_dataset(latest_file)
    if 'depth' in ds.dims: ds = ds.isel(depth=0)
    latest = ds.isel(time=-1)
    time_str = np.datetime_as_string(latest.time.values, unit='D')
    
    # EUROPE PLOT
    _generate_map(latest, var_name, conf, "europe", plots_dir, time_str)
    
    # LOCAL PLOTS — only domains defined in config (e.g. OBSEA; GALWAY excluded)
    local_domains = [d for d in ["OBSEA", "GALWAY"] if d in DOMAINS]
    for dom in local_domains:
        try:
            bbox = DOMAINS[dom]
            # Load Bathymetry for this domain
            bat_path = os.path.join(base_dir, f"datasets/bathymetry/{dom}_bathymetry.nc")
            ds_bat = None
            if os.path.exists(bat_path):
                ds_bat = xr.open_dataset(bat_path).rename({'latitude': 'lat', 'longitude': 'lon'})
                ds_bat = ds_bat.sel(lat=slice(bbox[1], bbox[3]), lon=slice(bbox[0], bbox[2]))

            # On-the-fly 200m interpolation for the map
            plot_res = 0.002
            new_lat = np.arange(bbox[1], bbox[3], plot_res)
            new_lon = np.arange(bbox[0], bbox[2], plot_res)
            
            latest_dom = latest.sel(lat=slice(bbox[1], bbox[3]), lon=slice(bbox[0], bbox[2]))
            latest_smooth = latest_dom.interp(lat=new_lat, lon=new_lon, method="linear")
            latest_smooth = latest_smooth.fillna(latest_dom.interp(lat=new_lat, lon=new_lon, method="nearest"))
            
            # Mask with topo
            if ds_bat is not None:
                bat_interp = ds_bat["elevation"].interp(lat=new_lat, lon=new_lon, method="linear")
                latest_smooth = latest_smooth.where(bat_interp < 0)
            
            _generate_map(latest_smooth, var_name, conf, dom.lower(), plots_dir, time_str, ds_bat=ds_bat)
        except Exception as e:
            print(f"Error {dom}: {e}")

if __name__ == "__main__":
    from pipeline.config import PIPELINE_CONFIG
    for v in ["sst", "sal", "temp_3d", "cur"]:
        plot_unified_maps(v, PIPELINE_CONFIG)
