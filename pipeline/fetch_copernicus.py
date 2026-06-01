import copernicusmarine
import os
import datetime
from pipeline.config import DOMAINS

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

def download_variable(var_name, config_dict, days_history=7, max_depth_local=300):
    scripts_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.dirname(scripts_dir)
    
    if var_name not in config_dict:
        print(f"Error: Variable '{var_name}' not found in configuration.")
        return

    conf = config_dict[var_name]
    is_3d = conf.get("is_3d", False)
    
    end_date = datetime.datetime.utcnow()
    start_date = end_date - datetime.timedelta(days=days_history)
    start_date_str = start_date.strftime("%Y-%m-%d %H:%M:%S")
    end_date_str = end_date.strftime("%Y-%m-%d %H:%M:%S")

    print(f"Downloading {var_name} data from {start_date_str} to {end_date_str}")

    for region, product_id in conf["products"].items():
        if not is_3d:
            # Standard 2D European Download
            print(f"--- Downloading {region} {var_name} Data (Europe 2D) ---")
            out_dir = os.path.join(base_dir, "datasets", "raw", var_name, region)
            _execute_download(product_id, out_dir, conf["nc_vars"], start_date_str, end_date_str, DOMAINS["EUROPE"])
        else:
            # 3D Hybrid Download:
            # 1. Europe Column (for 3D layers and 2D surface maps)
            print(f"--- Downloading {region} {var_name} Data (Europe Column) ---")
            out_dir_euro = os.path.join(base_dir, "datasets", "raw", f"{var_name}_europe_column", region)
            _execute_download(product_id, out_dir_euro, conf["nc_vars"], start_date_str, end_date_str, DOMAINS["EUROPE"], max_depth=300)
            
            # 2. Local DTOs (Ultra-high res Full Column)
            for local_domain in ["OBSEA"]:
                print(f"--- Downloading {region} {var_name} Data ({local_domain} 3D) ---")
                out_dir_local = os.path.join(base_dir, "datasets", "raw", f"{var_name}_{local_domain.lower()}", region)
                _execute_download(product_id, out_dir_local, conf["nc_vars"], start_date_str, end_date_str, DOMAINS[local_domain], max_depth=max_depth_local)

if __name__ == "__main__":
    from pipeline.config import PIPELINE_CONFIG
    download_variable("sst", PIPELINE_CONFIG, days_history=1)
