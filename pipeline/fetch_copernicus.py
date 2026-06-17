import copernicusmarine
import os
import datetime
from pipeline.config import DOMAINS


def _get_nc_vars_for_region(conf, region):
    """
    Resolves nc_vars for a given region.
    Handles two cases:
      - nc_vars is a list  → uniform for all regions (P1D mode)
      - nc_vars is a dict  → per-region mapping (PT1H SST mixes satellite + model)
    """
    nc_vars_def = conf["nc_vars"]
    if isinstance(nc_vars_def, dict):
        return nc_vars_def.get(region, conf.get("nc_vars_default", list(nc_vars_def.values())[0]))
    return nc_vars_def


def _execute_download(product_id, out_dir, nc_vars, start_date_str, end_date_str, bbox, max_depth=None):
    os.makedirs(out_dir, exist_ok=True)
    kwargs = dict(
        dataset_id=product_id,
        output_directory=out_dir,
        variables=nc_vars,
        start_datetime=start_date_str,
        end_datetime=end_date_str,
        minimum_longitude=bbox[0],
        minimum_latitude=bbox[1],
        maximum_longitude=bbox[2],
        maximum_latitude=bbox[3],
        overwrite=True
    )

    if max_depth is not None:
        kwargs["minimum_depth"] = 0
        kwargs["maximum_depth"] = max_depth

    try:
        copernicusmarine.subset(**kwargs)
    except Exception as e:
        print(f"  Warning: Failed to download dataset {product_id}: {e}")
        print(f"  Attempting historical fallback (MY/REP) for {product_id}...")
        
        fallback_id = product_id
        if "_anfc_" in fallback_id:
            fallback_id = fallback_id.replace("_anfc_", "_my_")
        elif "_nrt_" in fallback_id:
            fallback_id = fallback_id.replace("_nrt_", "_my_")
        elif "_NRT_" in fallback_id:
            fallback_id = fallback_id.replace("_NRT_", "_REP_")
        
        if fallback_id != product_id:
            kwargs["dataset_id"] = fallback_id
            try:
                print(f"  Retrying with: {fallback_id}")
                copernicusmarine.subset(**kwargs)
            except Exception as e2:
                print(f"  Error: Fallback also failed for {fallback_id}: {e2}")
        else:
            print("  Error: No heuristic fallback pattern found for this product.")


def download_variable(var_name, config_dict, days_history=7, max_depth_local=300):
    scripts_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.dirname(scripts_dir)
    
    if var_name not in config_dict:
        print(f"Error: Variable '{var_name}' not found in configuration.")
        return

    conf = config_dict[var_name]
    is_3d = conf.get("is_3d", False)

    # For CHL in hourly mode, the actual download is daily regardless of output temporal_res.
    # source_temporal_res overrides the effective download cadence.
    source_res = conf.get("source_temporal_res", conf.get("temporal_res", "P1D"))
    
    end_date = datetime.datetime.utcnow()
    start_date = end_date - datetime.timedelta(days=days_history)
    start_date_str = start_date.strftime("%Y-%m-%d %H:%M:%S")
    end_date_str = end_date.strftime("%Y-%m-%d %H:%M:%S")

    print(f"Downloading {var_name} data from {start_date_str} to {end_date_str} (source cadence: {source_res})")

    for region, product_id in conf["products"].items():
        # Resolve the correct variables for this region (handles dict-per-region nc_vars)
        nc_vars = _get_nc_vars_for_region(conf, region)

        if not is_3d:
            # Standard 2D European Download
            print(f"--- Downloading {region} {var_name} Data (Europe 2D) | vars: {nc_vars} ---")
            out_dir = os.path.join(base_dir, "datasets", "raw", var_name, region)
            _execute_download(product_id, out_dir, nc_vars, start_date_str, end_date_str, DOMAINS["EUROPE"])
        else:
            # 3D Hybrid Download (Optimized for 2D surface only):
            # 1. Europe Surface (depth <= 2m)
            print(f"--- Downloading {region} {var_name} Data (Europe Surface) | vars: {nc_vars} ---")
            out_dir_euro = os.path.join(base_dir, "datasets", "raw", f"{var_name}_europe_column", region)
            _execute_download(product_id, out_dir_euro, nc_vars, start_date_str, end_date_str, DOMAINS["EUROPE"], max_depth=2)
            
            # 2. Local DTOs (Disabled as per user request to keep only 2D)
            # for local_domain in ["OBSEA"]:
            #     print(f"--- Downloading {region} {var_name} Data ({local_domain} 3D) ---")
            #     out_dir_local = os.path.join(base_dir, "datasets", "raw", f"{var_name}_{local_domain.lower()}", region)
            #     _execute_download(product_id, out_dir_local, nc_vars, start_date_str, end_date_str, DOMAINS[local_domain], max_depth=max_depth_local)

if __name__ == "__main__":
    from pipeline.config import PIPELINE_CONFIG
    download_variable("sst", PIPELINE_CONFIG, days_history=1)

