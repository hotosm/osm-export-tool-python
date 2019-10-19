import osm_export_tool
import osm_export_tool.tabular as tabular
import osm_export_tool.nontabular as nontabular
from osm_export_tool.mapping import Mapping
from osm_export_tool.geometry import load_geometry
from osm_export_tool.sources import Overpass, Pbf, OsmExpress, OsmiumTool
from osm_export_tool.package import create_package, create_posm_bundle
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

#source = Overpass('http://overpass.hotosm.org',geom,join(tempdir,'extract.osm.pbf'),tempdir=tempdir,mapping=mapping,use_existing=False)
source = OsmExpress('osmx','hawaii.osmx',geom,join(tempdir,'extract.osm.pbf'),tempdir=tempdir,use_existing=False)

shp = tabular.Shapefile("tmp/example",mapping)
gpkg = tabular.Geopackage("tmp/example",mapping)
kml = tabular.Kml("tmp/example",mapping)
tabular_outputs = [shp,gpkg,kml]

h = tabular.Handler(tabular_outputs,mapping)

h.apply_file(source.path(), locations=True, idx='sparse_file_array')

for output in tabular_outputs:
	output.finalize()

osmand_files = nontabular.osmand(source.path(),'tools/OsmAndMapCreator-main',tempdir=tempdir)
garmin_files = nontabular.garmin(source.path(),'tools/splitter-r583/splitter.jar','tools/mkgmap-r3890/mkgmap.jar',tempdir=tempdir)
#mwm_files = nontabular.mwm(source.path(),join(tempdir,'mwm'),'generate_mwm.sh','/usr/local/bin/generator_tool','/usr/bin/osmconvert')
#mbtiles_files = nontabular.mbtiles(geom,join(tempdir,'output.mbtiles'),'http://tile.openstreetmap.org/{z}/{x}/{y}.png',14,14)

files = []
files += shp.files
files += gpkg.files
files += kml.files
files += osmand_files
files += garmin_files
#files += mbtiles_files
files.append(osm_export_tool.File('osm_pbf',[source.path()],''))
create_package(join(tempdir,'shp.zip'),shp.files,boundary_geom=geom)
create_posm_bundle(join(tempdir,'bundle.tgz'),files,"Title","name","description",geom)