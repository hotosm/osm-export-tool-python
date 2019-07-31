import osmium as o
import re
try:
    import ogr
except ModuleNotFoundError:
    print('ERROR: Install the version of python package GDAL that corresponds to gdalinfo --version on your system.')
    exit(1)
from base64 import b64decode
from osm_export_tool import GeomType

fab = o.geom.WKBFactory()
create_geom = lambda b : ogr.CreateGeometryFromWkb(bytes.fromhex(b))

epsg_4326 = ogr.osr.SpatialReference()
epsg_4326.ImportFromEPSG(4326)

class Shapefile:
    class Layer:
        def __init__(self,driver,name,ogr_geom_type,keys):
            def launderName(col):
                return re.sub(r'[^a-zA-Z0-9_]', '', col)[0:10]

            self.columns = keys
            self.ds = driver.CreateDataSource(name + '.shp')
            self.ogr_layer = self.ds.CreateLayer('', epsg_4326, ogr_geom_type,options=['ENCODING=UTF-8'])
            self.launderedNames = {}
            for column in self.columns:
                laundered_name = launderName(column)
                field_name = ogr.FieldDefn(laundered_name, ogr.OFTString)
                field_name.SetWidth(254)
                self.ogr_layer.CreateField(field_name)
                self.launderedNames[column] = laundered_name

            self.defn = self.ogr_layer.GetLayerDefn()

    def __init__(self,output_name,mapping):
        driver = ogr.GetDriverByName('ESRI Shapefile')

        self.layers = {}
        for t in mapping.themes:
            # if the theme has only one geom type, don't add a suffix to the layer name.
            if t.points and not t.lines and not t.polygons:
                self.layers[(t.name,GeomType.POINT)] = Shapefile.Layer(driver,output_name + '_' + t.name,ogr.wkbPoint,t.keys)
            elif not t.points and t.lines and not t.polygons:
                self.layers[(t.name,GeomType.LINE)] = Shapefile.Layer(driver,output_name + '_' + t.name,ogr.wkbLineString,t.keys)
            elif not t.points and not t.lines and t.polygons:
                self.layers[(t.name,GeomType.POLYGON)] = Shapefile.Layer(driver,output_name + '_' + t.name,ogr.wkbMultiPolygon,t.keys)
            else:
                if t.points:
                    self.layers[(t.name,GeomType.POINT)] = Shapefile.Layer(driver,output_name + '_' + t.name + '_points',ogr.wkbPoint,t.keys)
                if t.lines:
                    self.layers[(t.name,GeomType.LINE)] = Shapefile.Layer(driver,output_name + '_' + t.name + '_lines',ogr.wkbLineString,t.keys)
                if t.polygons:
                    self.layers[(t.name,GeomType.POLYGON)] = Shapefile.Layer(driver,output_name + '_' + t.name + '_polygons',ogr.wkbMultiPolygon,t.keys)

    def write(self,layer_name,geom_type,geom,tags):
        layer = self.layers[(layer_name,geom_type)]
        feature = ogr.Feature(layer.defn)
        feature.SetGeometry(geom)
        for col in layer.columns:
            if col in tags:
                feature.SetField(layer.launderedNames[col],tags[col])
        layer.ogr_layer.CreateFeature(feature)

    def finalize(self):
        pass

class Geopackage:
    class Layer:
        def __init__(self,ds,name,ogr_geom_type,keys):
            self.ogr_layer = ds.CreateLayer(name, epsg_4326, ogr_geom_type,options=['SPATIAL_INDEX=NO'])
            self.columns = keys
            for column_name in self.columns:
                field_name = ogr.FieldDefn(column_name, ogr.OFTString)
                field_name.SetWidth(254)
                self.ogr_layer.CreateField(field_name)
            self.defn = self.ogr_layer.GetLayerDefn()

    def __init__(self,output_name,mapping):
        driver = ogr.GetDriverByName('GPKG')
        self.ds = driver.CreateDataSource(output_name + '.gpkg')
        self.ds.StartTransaction()

        self.layers = {}
        for theme in mapping.themes:
            layer = Geopackage.Layer(self.ds,theme.name,ogr.wkbUnknown,theme.keys)
            if theme.points:
                self.layers[(theme.name,GeomType.POINT)] = layer
            if theme.lines:
                self.layers[(theme.name,GeomType.LINE)] = layer
            if theme.polygons:
                self.layers[(theme.name,GeomType.POLYGON)] = layer

    def write(self,layer_name,geom_type,geom,tags):
        layer = self.layers[(layer_name,geom_type)]
        feature = ogr.Feature(layer.defn)
        feature.SetGeometry(geom)
        for column_name in layer.columns:
            if column_name in tags:
                feature.SetField(column_name,tags[column_name])
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
        if len(n.tags) == 0:
            return
        geom = None
        for theme in self.mapping.themes:
            if theme.matches(GeomType.POINT,n.tags):
                if not geom:
                    geom = create_geom(fab.create_point(n))
                for output in self.outputs:
                    output.write(theme.name,GeomType.POINT,geom,n.tags)

    def way(self, w):
        if len(w.tags) == 0:
            return
        try:
            geom = None
            for theme in self.mapping.themes:
                if theme.matches(GeomType.LINE,w.tags):
                    if not geom:
                        geom = create_geom(fab.create_linestring(w))
                    for output in self.outputs:
                        output.write(theme.name,GeomType.LINE,geom,w.tags)
        except RuntimeError:
            print("Incomplete way: {0}".format(w.id))

    def area(self,a):
        if len(a.tags) == 0:
            return
        try:
            geom = None
            for theme in self.mapping.themes:
                if theme.matches(GeomType.POLYGON,a.tags):
                    if not geom:
                        geom = create_geom(fab.create_multipolygon(a))
                    for output in self.outputs:
                        output.write(theme.name,GeomType.POLYGON,geom,a.tags)
        except RuntimeError:
            print('Invalid area: {0}'.format(a.orig_id()))


