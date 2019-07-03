import osmium as o
try:
    import ogr
except ModuleNotFoundError:
    print('ERROR: Install the version of python package GDAL that corresponds to gdalinfo --version on your system.')
    exit(1)
from base64 import b64decode

fab = o.geom.WKBFactory()
create_geom = lambda b : ogr.CreateGeometryFromWkb(bytes.fromhex(b))

from enum import Enum

class GeomType(Enum):
    POINT = 1
    LINE = 2
    POLYGON = 3

class Shapefile:
    class Layer:
        def __init__(self,driver,name,ogr_geom_type):
            self.cols = ['name']
            self.ds = driver.CreateDataSource(name + '.shp')
            self.ogr_layer = self.ds.CreateLayer('', None, ogr_geom_type)
            field_name = ogr.FieldDefn('name', ogr.OFTString)
            field_name.SetWidth(254)
            self.ogr_layer.CreateField(field_name)
            self.defn = self.ogr_layer.GetLayerDefn()

    def __init__(self,name):
        driver = ogr.GetDriverByName('ESRI Shapefile')

        self.layers = {}
        self.layers[('buildings',GeomType.POINT)] = Shapefile.Layer(driver,'buildings_points',ogr.wkbPoint)
        self.layers[('buildings',GeomType.LINE)] = Shapefile.Layer(driver,'buildings_lines',ogr.wkbLineString)
        self.layers[('buildings',GeomType.POLYGON)] = Shapefile.Layer(driver,'buildings_polygons',ogr.wkbMultiPolygon)

    def write(self,layer_name,geom_type,geom,tags):
        layer = self.layers[(layer_name,geom_type)]
        feature = ogr.Feature(layer.defn)
        feature.SetGeometry(geom)
        for col in layer.cols:
            if col in tags:
                feature.SetField(col,tags[col])
        layer.ogr_layer.CreateFeature(feature)

    def finalize(self):
        pass

class Geopackage:
    class Layer:
        def __init__(self,ds,name,ogr_geom_type):
            self.cols = ['name']
            self.ogr_layer = ds.CreateLayer(name, None, ogr_geom_type)
            field_name = ogr.FieldDefn('name', ogr.OFTString)
            field_name.SetWidth(254)
            self.ogr_layer.CreateField(field_name)
            self.defn = self.ogr_layer.GetLayerDefn()

    def __init__(self,name):
        driver = ogr.GetDriverByName('GPKG')
        self.ds = driver.CreateDataSource(name + '.gpkg')
        self.ds.StartTransaction()
        self.layers = {}
        self.layers[('buildings',GeomType.POINT)] = Geopackage.Layer(self.ds,'buildings_points',ogr.wkbPoint)
        self.layers[('buildings',GeomType.LINE)] = Geopackage.Layer(self.ds,'buildings_lines',ogr.wkbLineString)
        self.layers[('buildings',GeomType.POLYGON)] = Geopackage.Layer(self.ds,'buildings_polygons',ogr.wkbMultiPolygon)

    def write(self,layer_name,geom_type,geom,tags):
        layer = self.layers[(layer_name,geom_type)]
        feature = ogr.Feature(layer.defn)
        feature.SetGeometry(geom)
        for col in layer.cols:
            if col in tags:
                feature.SetField(col,tags[col])
        layer.ogr_layer.CreateFeature(feature)

    def finalize(self):
        self.ds.CommitTransaction()
        self.layers = None
        self.ds = None

class Handler(o.SimpleHandler):
    def __init__(self,outputs,mapping):
        super(Handler, self).__init__()
        self.outputs = outputs
        self.mapping = mapping

    def node(self,n):
        geom = None
        for layer_name in self.mapping.match(n.tags,GeomType.POINT):
            if not geom:
                geom = create_geom(fab.create_point(n))
            for output in self.outputs:
                output.write(layer_name,GeomType.POINT,geom,n.tags)

    def way(self, w):
        try:
            geom = None
            for layer_name in self.mapping.match(w.tags,GeomType.LINE):
                if not geom:
                    geom = create_geom(fab.create_linestring(w))
                for output in self.outputs:
                    output.write(layer_name,GeomType.LINE,geom,w.tags)
        except RuntimeError:
            print("Incomplete way: {0}".format(w.id))

    def area(self,a):
        try:
            geom = None
            for layer_name in self.mapping.match(a.tags,GeomType.POLYGON):
                if not geom:
                    geom = create_geom(fab.create_multipolygon(a))
                for output in self.outputs:
                    output.write(layer_name,GeomType.POLYGON,geom,a.tags)
        except RuntimeError:
            print('Invalid area: {0}'.format(a.orig_id()))


