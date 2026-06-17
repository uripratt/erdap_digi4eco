#!/bin/bash
set -e
echo "Starting data fetch and mesh generation..."
python fetch_april_may_all.py
echo "Consolidating to monthly..."
python consolidate_to_monthly.py
echo "Checking times..."
python check_nc_times.py > local_times_output.txt
echo "Syncing with digi4eco..."
rsync -avz --delete ./datasets/ digi4eco:/datasets/
echo "Triggering reload..."
ssh digi4eco "touch /home/upc/erddap/conf/flag/forceReload"
echo "Done!"
