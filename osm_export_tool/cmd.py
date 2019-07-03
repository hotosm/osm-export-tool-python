#!/usr/bin/python
import sys
import time
import argparse
from osm_export_tool import export

def main():
	parser = argparse.ArgumentParser(description='Export OSM data in other file formats.')
	parser.add_argument('osm_file',  help='OSM .pbf or .xml input file')
	parser.add_argument('output_name', help='Output prefix')
	parser.add_argument('-f','--formats', dest='formats',default='gpkg',help='List of formats e.g. gpkg,shp,kml (default: gpkg)')
	parser.add_argument('-v','--verbose', action='store_true')
	parsed = parser.parse_args()

	formats = parsed.formats.split(',')
	outputs = []
	if 'gpkg' in formats:
		outputs.append(export.Geopackage(parsed.output_name))
	if 'shp' in formats:
		outputs.append(export.Shapefile(parsed.output_name))
	if 'kml' in formats:
		outputs.append(export.Kml(parsed.output_name))
	h = export.Handler(outputs)
	start_time = time.time()
	h.apply_file(parsed.osm_file, locations=True, idx='sparse_file_array')

	for output in outputs:
		output.finalize()
	print(time.time() - start_time)

if __name__ == '__main__':
	main()
