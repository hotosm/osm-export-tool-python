import osmium as o
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
        def __init__(self,driver,name,ogr_geom_type):
            self.cols = ['name']
            self.ds = driver.CreateDataSource(name + '.shp')
            self.ogr_layer = self.ds.CreateLayer('', epsg_4326, ogr_geom_type)
            field_name = ogr.FieldDefn('name', ogr.OFTString)
            field_name.SetWidth(254)
            self.ogr_layer.CreateField(field_name)
            self.defn = self.ogr_layer.GetLayerDefn()

    def __init__(self,output_name,mapping):
        driver = ogr.GetDriverByName('ESRI Shapefile')

        self.layers = {}
        for theme in mapping.themes:
            if 'points' in mapping.geom_types(theme):
                self.layers[(theme,GeomType.POINT)] = Shapefile.Layer(driver,output_name + '_' + theme + '_points',ogr.wkbPoint)
            if 'lines' in mapping.geom_types(theme):
                self.layers[(theme,GeomType.LINE)] = Shapefile.Layer(driver,output_name + '_' + theme + '_lines',ogr.wkbLineString)
            if 'polygons' in mapping.geom_types(theme):
                self.layers[(theme,GeomType.POLYGON)] = Shapefile.Layer(driver,output_name + '_' + theme + '_polygons',ogr.wkbMultiPolygon)

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
        def __init__(self,ds,name,ogr_geom_type,keys):
            self.columns = keys
            self.ogr_layer = ds.CreateLayer(name, epsg_4326, ogr_geom_type)
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
            if theme.points:
                self.layers[(theme.name,GeomType.POINT)] = Geopackage.Layer(self.ds,theme.name + '_points',ogr.wkbPoint,theme.keys)
            if theme.lines:
                self.layers[(theme.name,GeomType.LINE)] = Geopackage.Layer(self.ds,theme.name + '_lines',ogr.wkbLineString,theme.keys)
            if theme.polygons:
                self.layers[(theme.name,GeomType.POLYGON)] = Geopackage.Layer(self.ds,theme.name + '_polygons',ogr.wkbMultiPolygon,theme.keys)

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
        geom = None
        for theme in self.mapping.themes:
            if theme.matches(GeomType.POINT,n.tags):
                if not geom:
                    geom = create_geom(fab.create_point(n))
                for output in self.outputs:
                    output.write(theme.name,GeomType.POINT,geom,n.tags)

    def way(self, w):
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


