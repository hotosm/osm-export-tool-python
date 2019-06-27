import osmium as o
try:
    import ogr
except ModuleNotFoundError:
    print('ERROR: Install the version of python package GDAL that corresponds to gdalinfo --version on your system.')
    exit(1)
import sys
from base64 import b64decode
import time

fab = o.geom.WKBFactory()
create_geom = lambda b : ogr.CreateGeometryFromWkb(bytes.fromhex(b))

class Shapefile:
    def __init__(self,name):
        driver = ogr.GetDriverByName('ESRI Shapefile')
        self.point_ds = driver.CreateDataSource(name + '_points.shp')
        self.point_layer = self.point_ds.CreateLayer('', None, ogr.wkbPoint)
        self.line_ds = driver.CreateDataSource(name + '_lines.shp')
        self.line_layer = self.line_ds.CreateLayer('', None, ogr.wkbLineString)
        self.polygon_ds = driver.CreateDataSource(name + '_polygons.shp')
        self.polygon_layer = self.polygon_ds.CreateLayer('', None, ogr.wkbMultiPolygon)

    def write_point(self,geom):
        feat = ogr.Feature(self.point_layer.GetLayerDefn())
        feat.SetGeometry(geom)
        self.point_layer.CreateFeature(feat)

    def write_line(self,geom):
        feat = ogr.Feature(self.line_layer.GetLayerDefn())
        feat.SetGeometry(geom)
        self.line_layer.CreateFeature(feat)

    def write_polygon(self,geom):
        feat = ogr.Feature(self.polygon_layer.GetLayerDefn())
        feat.SetGeometry(geom)
        self.polygon_layer.CreateFeature(feat)

class Geopackage:
    def __init__(self,name):
        driver = ogr.GetDriverByName('GPKG')
        self.ds = driver.CreateDataSource(name + '.gpkg')
        self.ds.StartTransaction()
        self.point_layer = self.ds.CreateLayer('points', None, ogr.wkbPoint)
        self.line_layer = self.ds.CreateLayer('lines', None, ogr.wkbLineString)
        self.polygon_layer = self.ds.CreateLayer('polygons', None, ogr.wkbMultiPolygon)

    def write_point(self,geom):
        feat = ogr.Feature(self.point_layer.GetLayerDefn())
        feat.SetGeometry(geom)
        self.point_layer.CreateFeature(feat)

    def write_line(self,geom):
        feat = ogr.Feature(self.line_layer.GetLayerDefn())
        feat.SetGeometry(geom)
        self.line_layer.CreateFeature(feat)

    def write_polygon(self,geom):
        feat = ogr.Feature(self.polygon_layer.GetLayerDefn())
        feat.SetGeometry(geom)
        self.polygon_layer.CreateFeature(feat)

    def finalize(self):
        self.ds.CommitTransaction()
        self.point_layer = None
        self.line_layer = None
        self.polygon_layer = None
        self.ds = None


class Handler(o.SimpleHandler):
    def __init__(self,outputs):
        super(Handler, self).__init__()
        self.outputs = outputs

    def node(self,n):
        if len(n.tags) > 0:
            geom = create_geom(fab.create_point(n))
            for output in self.outputs:
                output.write_point(geom)

    def way(self, w):
        if len(w.tags) > 0:
            geom = create_geom(fab.create_linestring(w))
            for output in self.outputs:
                output.write_line(geom)

    def area(self,a):
        try:
            if len(a.tags) > 0:
                geom = create_geom(fab.create_multipolygon(a))
                for output in self.outputs:
                    output.write_polygon(geom)
        except RuntimeError:
            print('Invalid area: {0}'.format(a.orig_id()))


def main(osmfile):
    start_time = time.time()
    gpkg = Geopackage(sys.argv[2])
    shp = Shapefile(sys.argv[2])
    h = Handler([gpkg])
    h.apply_file(osmfile, locations=True)
    gpkg.finalize()
    print(time.time() - start_time)

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Usage: python %s <osmfile> <name>" % sys.argv[0])
        sys.exit(-1)

    exit(main(sys.argv[1]))