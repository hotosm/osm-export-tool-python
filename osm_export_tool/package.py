import json
import os
from os.path import basename
import zipfile
import tarfile
import io
from shapely.geometry import mapping
from osm_export_tool import File

def create_package(destination,files,boundary_geom=None,output_name='zip'):
    with zipfile.ZipFile(destination, 'w', zipfile.ZIP_DEFLATED, True) as z:
        if boundary_geom:
            z.writestr("clipping_boundary.geojson", json.dumps(mapping(boundary_geom)))
        for file in files:
            for part in file.parts:
                z.write(part, os.path.basename(part))

    return File(output_name,[destination])

def create_posm_bundle(destination,files,title,name,description,geom):
    contents = {}
    with tarfile.open(destination, "w|gz") as bundle:
        for file in files:
            for part in file.parts:
                if file.output_name == 'shp':
                    target = 'data/' + basename(part)
                    contents[target] = {'Type':'ESRI Shapefile'}
                elif file.output_name == 'kml':
                    target = 'data/' + basename(part)
                    contents[target] = {'Type':'KML'}
                elif file.output_name == 'gpkg':
                    target = 'data/' + basename(part)
                    contents[target] = {'Type':'Geopackage'}
                elif file.output_name == 'osmand_obf':
                    target = 'navigation/' + basename(part)
                    contents[target] = {'Type':'OsmAnd'}
                elif file.output_name == 'garmin':
                    target = 'navigation/' + basename(part)
                    contents[target] = {'Type':'Garmin IMG'}
                elif file.output_name == 'mwm':
                    target = 'navigation/' + basename(part)
                    contents[target] = {'Type':'Maps.me'}
                elif file.output_name == 'osm_pbf':
                    target = 'osm/' + basename(part)
                    contents[target] = {'Type':'OSM/PBF'}
                elif file.output_name == 'mbtiles':
                    target = 'tiles/' + basename(part)
                    contents[target] = {
                        'type':'MBTiles',
                        'minzoom':file.extra['minzoom'],
                        'maxzoom':file.extra['maxzoom'],
                        'source':file.extra['source']
                    }
                bundle.add(part,target)

        data = json.dumps({
            'title':title,
            'name':name,
            'description':description,
            'bbox':geom.bounds,
            'contents':contents
        },indent=2).encode()
        tarinfo = tarfile.TarInfo('manifest.json')
        tarinfo.size = len(data)
        bundle.addfile(tarinfo, io.BytesIO(data))

    return File('bundle',[destination])
