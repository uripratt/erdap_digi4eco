import sys
import os

conf_file = "conf/datasets.xml"
with open(conf_file, "rb") as f:
    content = f.read().decode("utf-8", "ignore")

pres_block = """
    <dataVariable>
        <sourceName>pres</sourceName>
        <destinationName>pres</destinationName>
        <dataType>double</dataType>
        <addAttributes>
            <att name="units">dbar</att>
        </addAttributes>
    </dataVariable>
"""

if 'datasetID="obsea_local_dto"' in content:
    print("Found obsea_local_dto dataset.")
    parts = content.split('datasetID="obsea_local_dto"')
    # The dataset block ends at the next </dataset>
    subparts = parts[1].split('</dataset>')
    # Check if pres is already there
    if '<sourceName>pres</sourceName>' not in subparts[0]:
        subparts[0] += pres_block
        parts[1] = '</dataset>'.join(subparts)
        new_content = 'datasetID="obsea_local_dto"'.join(parts)
        with open(conf_file, "w", encoding="utf-8") as f:
            f.write(new_content)
        print("Successfully added Pressure to datasets.xml")
    else:
        print("Pressure already exists in datasets.xml")
else:
    print("Could not find obsea_local_dto dataset.")
