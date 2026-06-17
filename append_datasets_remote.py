import subprocess
import os

print("Restoring and merging datasets...")

# Paths
local_xml_path = "/home/uripratt/Documents/SARTI/PROJECTS/DEGI4ECO/erddap/erddap_digi4models/conf/datasets.xml"
remote_temp_path = "/tmp/remote_datasets.xml"
remote_target = "digi4eco:/home/upc/erddap/conf/datasets.xml"

# 1. Download current remote datasets.xml (which we just restored to backup state)
subprocess.run(["scp", remote_target, remote_temp_path], check=True)

# 2. Read the local datasets.xml to extract the new datasets
with open(local_xml_path, "r", encoding="ISO-8859-1") as f:
    local_content = f.read()

# We extract the block of our 5 datasets
# It starts around Group A: 2D EUROPE PRODUCTS
start_idx = local_content.find("<!-- GROUP A: 2D EUROPE PRODUCTS")
if start_idx == -1:
    # Try alternate search
    start_idx = local_content.find("<dataset type=\"EDDGridFromNcFiles\" datasetID=\"unified_europe_sst\"")

end_idx = local_content.rfind("</dataset>") + len("</dataset>")

new_datasets_block = local_content[start_idx:end_idx]

# 3. Read the remote datasets.xml
with open(remote_temp_path, "r", encoding="ISO-8859-1") as f:
    remote_content = f.read()

# 4. Insert the new datasets block right before the closing </erddapDatasets> tag
closing_tag = "</erddapDatasets>"
insert_idx = remote_content.rfind(closing_tag)

if insert_idx == -1:
    print("Error: Could not find </erddapDatasets> in remote file.")
    exit(1)

merged_content = (
    remote_content[:insert_idx] +
    "\n\n<!-- ============================================================ -->\n" +
    "<!-- ADDED BY DIGI4ECO PIPELINE (NEW EUROPE 2D DATASETS)           -->\n" +
    "<!-- ============================================================ -->\n\n" +
    new_datasets_block +
    "\n\n" +
    remote_content[insert_idx:]
)

# 5. Write the merged content back to the temporary file
with open(remote_temp_path, "w", encoding="ISO-8859-1") as f:
    f.write(merged_content)

# 6. Upload the merged file back to the remote server
subprocess.run(["scp", remote_temp_path, remote_target], check=True)

# Clean up temp file
if os.path.exists(remote_temp_path):
    os.remove(remote_temp_path)

print("Merged datasets.xml successfully uploaded!")

# 7. Trigger reload
subprocess.run(["ssh", "digi4eco", "touch /home/upc/erddap/conf/flag/forceReload"], check=True)
print("Triggered forceReload on remote server.")
