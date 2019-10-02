import json
import os
import zipfile
from shapely.geometry import mapping
from osm_export_tool import File

def create_package(destination,files,boundary_geom=None):
    # the created zipfile must end with only .zip (not .shp.zip) for the HDX preview to work.
    with zipfile.ZipFile(destination, 'w', zipfile.ZIP_DEFLATED, True) as z:

        if boundary_geom:
            z.writestr("clipping_boundary.geojson", json.dumps(mapping(boundary_geom)))
        for file in files:
            for part in file.parts:
                z.write(part, os.path.basename(part))

    return File('zip',[destination],'')