import os
import glob
import xarray as xr
import numpy as np

datasets = {
    "sst": ("/home/uripratt/Documents/SARTI/PROJECTS/DEGI4ECO/erddap/erddap_digi4models/datasets/unified_europe_sst", "analysed_sst"),
    "chl": ("/home/uripratt/Documents/SARTI/PROJECTS/DEGI4ECO/erddap/erddap_digi4models/datasets/unified_europe_chl", "CHL"),
    "waves_VHM0": ("/home/uripratt/Documents/SARTI/PROJECTS/DEGI4ECO/erddap/erddap_digi4models/datasets/unified_europe_waves", "VHM0"),
    "waves_VMDR": ("/home/uripratt/Documents/SARTI/PROJECTS/DEGI4ECO/erddap/erddap_digi4models/datasets/unified_europe_waves", "VMDR"),
    "waves_VTPK": ("/home/uripratt/Documents/SARTI/PROJECTS/DEGI4ECO/erddap/erddap_digi4models/datasets/unified_europe_waves", "VTPK"),
}

for name, (folder, var) in datasets.items():
    files = glob.glob(os.path.join(folder, "*.nc"))
    if not files:
        print(f"No files for {name}")
        continue
    
    # Just take one recent file
    f = sorted(files)[-1]
    try:
        ds = xr.open_dataset(f)
        vals = ds[var].values
        # Drop nans
        vals = vals[~np.isnan(vals)]
        if len(vals) == 0:
            print(f"{name}: Empty")
            continue
            
        p1 = np.nanpercentile(vals, 1)
        p99 = np.nanpercentile(vals, 99)
        
        # Apply offset to sst since we added it in ERDDAP
        if name == "sst":
            p1 -= 273.15
            p99 -= 273.15
            
        print(f"{name} ({var}): Min (1%): {p1:.2f}, Max (99%): {p99:.2f}")
    except Exception as e:
        print(f"Error reading {name}: {e}")
