import os
import sys
import time
import argparse
import osm_export_tool.export as export
from osm_export_tool.mapping import Mapping
from osm_export_tool.geometry import load_geometry

def main():
	parser = argparse.ArgumentParser(description='Export OSM data in other file formats.')
	parser.add_argument('osm_file',  help='OSM .pbf or .xml input file')
	parser.add_argument('output_name', help='Output prefix')
	parser.add_argument('-f','--formats', dest='formats',default='gpkg',help='List of formats e.g. gpkg,shp,kml (default: gpkg)')
	parser.add_argument('-m','--mapping', dest='mapping',help='YAML mapping of features schema. If not specified, a default is used.')
	parser.add_argument('--clip', dest='clip',help='GeoJSON or POLY file to clip geometries.')
	parser.add_argument('-v','--verbose', action='store_true')
	parser.add_argument('--omit-osm-ids', action='store_true')
	parsed = parser.parse_args()

	mapping_txt = None
	if parsed.mapping:
		with open(parsed.mapping,'r') as f:
			mapping_txt = f.read()
	else:
		default_mapping = os.path.join(os.path.dirname(__file__), '../mappings/default.yml')
		with open(default_mapping,'r') as f:
			mapping_txt = f.read()
	
	mapping = Mapping(mapping_txt,default_osm_id=not parsed.omit_osm_ids)

	clipping_geom = None
	if parsed.clip:
		with open(parsed.clip,'r') as f:
			clipping_geom = load_geometry(f.read())

	formats = parsed.formats.split(',')
	outputs = []
	if 'gpkg' in formats:
		outputs.append(export.Geopackage(parsed.output_name,mapping))
	if 'shp' in formats:
		outputs.append(export.Shapefile(parsed.output_name,mapping))
	if 'kml' in formats:
		outputs.append(export.Kml(parsed.output_name,mapping))
	h = export.Handler(outputs,mapping,clipping_geom=clipping_geom)
	start_time = time.time()
	h.apply_file(parsed.osm_file, locations=True, idx='sparse_file_array')

	for output in outputs:
		output.finalize()

	print('Completed in {0} seconds.'.format(time.time() - start_time))

	for output in outputs:
		for file in output.files:
			print(file)