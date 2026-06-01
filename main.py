import argparse
import sys

from pipeline.config import PIPELINE_CONFIG
from pipeline.fetch_copernicus import download_variable
from pipeline.build_mesh import build_european_mesh
from pipeline.build_mesh_3d import build_european_mesh_3d
from visualization.plot_unified_maps import plot_unified_maps
from visualization.plot_unified_profiles import plot_unified_profile
from visualization.plot_unified_layers import plot_unified_layers

def main():
    parser = argparse.ArgumentParser(description="Orchestrate the Unified Multi-variable Pipeline")
    parser.add_argument("--skip-download", action="store_true", help="Skip the dataset download step")
    parser.add_argument("--skip-mesh", action="store_true", help="Skip the mesh building step")
    parser.add_argument("--skip-plot", action="store_true", help="Skip the map plotting step")
    parser.add_argument("--historical", action="store_true", help="Process all downloaded historical dates instead of just NRT (latest)")
    parser.add_argument("--days", type=int, help="Number of days to download from Copernicus (overrides default)")
    parser.add_argument("--vars", nargs="+", help="Specific variables to run (e.g., sst chl). Default: all", default=None)
    
    args = parser.parse_args()

    print("=== Starting Unified Multi-Variable Pipeline ===")
    
    # Determine which variables to run
    vars_to_run = args.vars if args.vars else list(PIPELINE_CONFIG.keys())
    
    # Validate vars against config
    for v in vars_to_run:
        if v not in PIPELINE_CONFIG:
            print(f"Error: Variable '{v}' is not defined in config.py")
            sys.exit(1)

    try:
        # Step 1: Download from Copernicus
        if not args.skip_download:
            print("\n[Step 1] Downloading data...")
            for v in vars_to_run:
                # Priority: 1. User specified --days, 2. Default for 3D (1 day), 3. Default for 2D (7 days)
                if args.days:
                    days_to_download = args.days
                else:
                    days_to_download = 1 if PIPELINE_CONFIG[v].get("is_3d", False) else 7
                
                print(f"  Downloading {v} for {days_to_download} days...")
                download_variable(v, PIPELINE_CONFIG, days_history=days_to_download)
        else:
            print("\n[Step 1] Skipping dataset downloads...")

        # Step 2: Build Mesh
        if not args.skip_mesh:
            print(f"\n[Step 2] Building Meshes (Historical Mode: {args.historical})...")
            for v in vars_to_run:
                print(f"\n  -> Building {v} mesh (Europe 2D Surface)...")
                build_european_mesh(v, PIPELINE_CONFIG, historical=args.historical)
                
                if PIPELINE_CONFIG[v].get("is_3d", False):
                    print(f"  -> Building {v} mesh (Local 3D DTOs)...")
                    build_european_mesh_3d(v, PIPELINE_CONFIG, historical=args.historical)
        else:
            print("\n[Step 2] Skipping mesh building...")

        # Step 3: Plot
        if not args.skip_plot:
            print("\n[Step 3] Generating Plots...")
            for v in vars_to_run:
                print(f"  -> Plotting Map for {v}...")
                plot_unified_maps(v, PIPELINE_CONFIG)
                
                # Special 3D visualizations
                if PIPELINE_CONFIG[v].get("is_3d", False):
                    print(f"  -> Generating OBSEA 3D Profile Plot ({v})...")
                    plot_unified_profile(v, PIPELINE_CONFIG)
                    print(f"  -> Generating 3D Layers Plot ({v})...")
                    plot_unified_layers(v, PIPELINE_CONFIG)
        else:
            print("\n[Step 3] Skipping map generation...")

        print("\n=== Pipeline Completed Successfully ===")

    except Exception as e:
        print(f"\n[ERROR] Pipeline failed during execution: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
