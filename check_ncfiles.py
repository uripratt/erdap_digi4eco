import xarray as xr
import rich as r

ds = xr.open_dataset("/home/uripratt/Documents/SARTI/PROJECTS/DEGI4ECO/erddap/erddap_digi4models/datasets/unified_europe_sst/EUROPE_TOTAL_1KM_sst_202605.nc")
print(ds)

r.print(ds.variables.keys())
