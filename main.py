import argparse
import sys

from scripts.fetch_copernicus import download_all, download_3d_all
from scripts.build_mesh import build_european_mesh
from scripts.build_mesh_3d import build_european_mesh_3d
from scripts.plot_unified_sst import plot_unified_sst
from scripts.plot_3d_profile import plot_obsea_profile
from scripts.plot_3d_layers import plot_temperature_layers

def main():
    parser = argparse.ArgumentParser(description="Orchestrate the Unified SST Map Pipeline")
    parser.add_argument("--skip-download", action="store_true", help="Skip the dataset download step")
    parser.add_argument("--skip-mesh", action="store_true", help="Skip the mesh building step")
    parser.add_argument("--skip-plot", action="store_true", help="Skip the map plotting step")
    parser.add_argument("--3d", dest="enable_3d", action="store_true", help="Enable 3D temperature pipeline")
    
    args = parser.parse_args()

    print("=== Starting Unified SST Pipeline ===")

    try:
        # Step 1: Download from Copernicus
        if not args.skip_download:
            print("\n[Step 1] Downloading 2D SST data...")
            download_all(days_history=7)
            if args.enable_3d:
                print("\n[Step 1.b] Downloading 3D Physics data...")
                download_3d_all(days_history=1)
        else:
            print("\n[Step 1] Skipping dataset downloads...")

        # Step 2: Build Mesh
        if not args.skip_mesh:
            print("\n[Step 2] Building European Unified Mesh (2D)...")
            build_european_mesh()
            if args.enable_3d:
                print("\n[Step 2.b] Building European Unified Mesh (3D)...")
                build_european_mesh_3d()
        else:
            print("\n[Step 2] Skipping mesh building...")

        # Step 3: Plot
        if not args.skip_plot:
            print("\n[Step 3] Generating Plots...")
            print("  - Generating 2D SST Plot...")
            plot_unified_sst()
            if args.enable_3d:
                print("  - Generating OBSEA 3D Profile Plot...")
                plot_obsea_profile()
                print("  - Generating 3D Temperature Layers Plot...")
                plot_temperature_layers()
        else:
            print("\n[Step 3] Skipping map generation...")

        print("\n=== Pipeline Completed Successfully ===")

    except Exception as e:
        print(f"\n[ERROR] Pipeline failed during execution: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
