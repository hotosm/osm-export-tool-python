import osm_export_tool
import osm_export_tool.tabular as tabular
import osm_export_tool.nontabular as nontabular
from osm_export_tool.mapping import Mapping
from osm_export_tool.geometry import load_geometry
from osm_export_tool.sources import Overpass, File
from os.path import join

GEOJSON = """{
	"type": "MultiPolygon",
    "coordinates": [[
    	[
            [-155.077815, 19.722514],
            [-155.087643, 19.722514],
            [-155.087643, 19.715929],
            [-155.077815, 19.715929],
            [-155.077815, 19.722514]
		]
	]]
}"""

geom = load_geometry(GEOJSON)
tempdir = 'tmp'

with open('../osm_export_tool/mappings/default.yml','r') as f:
	mapping_txt = f.read()
mapping = Mapping(mapping_txt)

source = Overpass('http://overpass.hotosm.org',geom,join(tempdir,'overpass.osm.pbf'),tempdir=tempdir,mapping=mapping)

shp = tabular.Shapefile("tmp/example",mapping)
gpkg = tabular.Geopackage("tmp/example",mapping)
kml = tabular.Kml("tmp/example",mapping)
tabular_outputs = [shp,gpkg,kml]

h = tabular.Handler(tabular_outputs,mapping)

h.apply_file(source.path(), locations=True, idx='sparse_file_array')

for output in tabular_outputs:
	output.finalize()

nontabular.Osmand(source.path(),'tools/OsmAndMapCreator-main',tempdir=tempdir).run()
nontabular.Garmin(source.path(),'tools/splitter-r583/splitter.jar','tools/mkgmap-r3890/mkgmap.jar',tempdir=tempdir).run()
nontabular.Mwm(source.path(),'tools/generate_mwm.sh',tempdir=tempdir).run()
print(shp.files)
print(gpkg.files)
print(kml.files)
