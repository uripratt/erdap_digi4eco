#!/bin/bash

# Digi4ECO Daily Automation Script
# This script is designed to be run daily via cron.
# It performs the full operational lifecycle:
# 1. Fetches NRT data from Copernicus
# 2. Builds unified European grids
# 3. Generates future predictions up to the end of the next month
# 4. Consolidates loose daily files into monthly files
# 5. Cleans up old datasets (disabled by default as per user request)
#
# Mode selection: set PIPELINE_MODE env variable before calling this script.
#   PIPELINE_MODE=daily   (default) → uses PIPELINE_CONFIG      (P1D products)
#   PIPELINE_MODE=hourly            → uses PIPELINE_CONFIG_HOURLY (PT1H products)
# Example: PIPELINE_MODE=hourly ./daily_automation.sh

MODE="${PIPELINE_MODE:-daily}"

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
BASE_DIR="$(dirname "$SCRIPT_DIR")"
VENV_PATH="$BASE_DIR/venv_digi4eco/bin/activate"

echo "========================================================="
echo "Starting Digi4ECO Daily Automation: $(date)"
echo "========================================================="

# Activate virtual environment if it exists
if [ -f "$VENV_PATH" ]; then
    echo "Activating virtual environment..."
    source "$VENV_PATH"
else
    echo "Warning: Virtual environment not found at $VENV_PATH"
    echo "Using system python..."
fi

cd "$BASE_DIR"

echo ""
echo ">>> STEP 1 & 2: Fetch Copernicus NRT Data & Build Meshes [mode=$MODE]"
# The existing main.py or run_fetch_all.py typically handles the daily fetch
# If run_fetch_all.py exists, we use it, otherwise we fall back to main.py
if [ -f "run_fetch_all.py" ]; then
    python run_fetch_all.py --mode "$MODE"
elif [ -f "main.py" ]; then
    python main.py --mode "$MODE"
else
    echo "Error: Neither run_fetch_all.py nor main.py found."
fi

echo ""
echo ">>> STEP 3: Generate Future Predictions [mode=$MODE]"
python pipeline/predict_future.py --mode "$MODE"

echo ""
echo ">>> STEP 4: Consolidate Monthly NetCDF Files"
python consolidate_to_monthly.py

echo ""
echo ">>> STEP 5: Trigger ERDDAP Reload"
python check_erddap.py

# echo ""
# echo ">>> STEP 6: Clean up old data (> 2 months)"
# NOTE: Currently disabled per user request ("no borres nada de momento")
# find "$BASE_DIR/datasets/" -type f -name "*_20*.nc" -mtime +60 -exec rm {} \;

echo "========================================================="
echo "Finished Digi4ECO Daily Automation: $(date)"
echo "========================================================="
