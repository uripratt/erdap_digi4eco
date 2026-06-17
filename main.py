import argparse
import sys

from pipeline.config import PIPELINE_CONFIG, PIPELINE_CONFIG_HOURLY
from pipeline.fetch_copernicus import download_variable
from pipeline.build_mesh import build_european_mesh
from pipeline.build_mesh_3d import build_european_mesh_3d
from pipeline.predict_future import generate_predictions
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
    parser.add_argument(
        "--mode",
        choices=["daily", "hourly"],
        default="daily",
        help="Pipeline mode: 'daily' = PIPELINE_CONFIG (P1D), 'hourly' = PIPELINE_CONFIG_HOURLY (PT1H)"
    )
    
    args = parser.parse_args()

    # Select the active configuration based on mode
    active_config = PIPELINE_CONFIG_HOURLY if args.mode == "hourly" else PIPELINE_CONFIG
    print(f"=== Starting Unified Multi-Variable Pipeline [mode={args.mode}] ===")
    
    # Determine which variables to run
    vars_to_run = args.vars if args.vars else list(active_config.keys())

    # Validate vars against config
    for v in vars_to_run:
        if v not in active_config:
            print(f"Error: Variable '{v}' is not defined in config.py for mode '{args.mode}'")
            sys.exit(1)

    try:
        # Step 1: Download from Copernicus
        if not args.skip_download:
            print("\n[Step 1] Downloading data...")
            for v in vars_to_run:
                if args.days:
                    days_to_download = args.days
                else:
                    days_to_download = 1 if active_config[v].get("is_3d", False) else 7

                print(f"  Downloading {v} for {days_to_download} days...")
                download_variable(v, active_config, days_history=days_to_download)
        else:
            print("\n[Step 1] Skipping dataset downloads...")

        # Step 2: Build Mesh
        if not args.skip_mesh:
            print(f"\n[Step 2] Building Meshes (Historical Mode: {args.historical})...")
            for v in vars_to_run:
                print(f"\n  -> Building {v} mesh (Europe 2D Surface)...")
                build_european_mesh(v, active_config, historical=args.historical)

                if active_config[v].get("is_3d", False):
                    print(f"  -> Building {v} mesh (Local 3D DTOs)...")
                    build_european_mesh_3d(v, active_config, historical=args.historical)
        else:
            print("\n[Step 2] Skipping mesh building...")

        # Step 3: Plot
        if not args.skip_plot:
            print("\n[Step 3] Generating Plots...")
            for v in vars_to_run:
                print(f"  -> Plotting Map for {v}...")
                plot_unified_maps(v, active_config)

                if active_config[v].get("is_3d", False):
                    print(f"  -> Generating OBSEA 3D Profile Plot ({v})...")
                    plot_unified_profile(v, active_config)
                    print(f"  -> Generating 3D Layers Plot ({v})...")
                    plot_unified_layers(v, active_config)
        else:
            print("\n[Step 3] Skipping map generation...")

        print("\n=== Pipeline Completed Successfully ===")

    except Exception as e:
        print(f"\n[ERROR] Pipeline failed during execution: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
