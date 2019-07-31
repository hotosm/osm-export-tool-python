import unittest
from osm_export_tool.mapping import Mapping
from osm_export_tool import GeomType

class TestMapping(unittest.TestCase):
    def test_basic_mapping(self):
        y = '''
        buildings:
          select:
            - name
        '''
        m = Mapping(y)
        self.assertEqual(len(m.themes),1)
        theme = m.themes[0]
        self.assertEqual(theme.name,'buildings')
        self.assertTrue(theme.points)
        self.assertTrue(theme.lines)
        self.assertTrue(theme.polygons)
        self.assertTrue('name' in theme.keys)

    def test_geom_types(self):
        y = '''
        buildings:
          types:
            - points
          select:
            - name
        '''
        m = Mapping(y)
        self.assertTrue(m.themes[0].points)
        self.assertFalse(m.themes[0].lines)
        self.assertFalse(m.themes[0].polygons)
        y = '''
        buildings:
          types:
            - lines
          select:
            - name
        '''
        m = Mapping(y)
        self.assertFalse(m.themes[0].points)
        self.assertTrue(m.themes[0].lines)
        self.assertFalse(m.themes[0].polygons)
        y = '''
        buildings:
          types:
            - polygons
          select:
            - name
        '''
        m = Mapping(y)
        self.assertFalse(m.themes[0].points)
        self.assertFalse(m.themes[0].lines)
        self.assertTrue(m.themes[0].polygons)
        

    def test_key_selections(self):
        y = '''
        buildings:
          types:
            - polygons
          select:
            - addr:housenumber
        '''
        m = Mapping(y)
        self.assertTrue('addr:housenumber' in m.themes[0].keys)

    def test_where(self):
        y = '''
        buildings:
          types:
            - polygons
          select:
            - addr:housenumber
          where:
            - building = 'yes'
        '''
        m = Mapping(y)
        self.assertFalse(m.themes[0].matches(GeomType.POINT,{'building':'yes'}))
        self.assertFalse(m.themes[0].matches(GeomType.POLYGON,{'building':'no'}))
        self.assertTrue(m.themes[0].matches(GeomType.POLYGON,{'building':'yes'}))

    def test_default_matcher(self):
        y = '''
        buildings:
          types:
            - polygons
          select:
            - addr:housenumber
        '''
        m = Mapping(y)
        self.assertTrue(m.themes[0].matches(GeomType.POLYGON,{'addr:housenumber':'1234'}))

    def test_multiple_matchers(self):
        y = '''
        buildings:
          types:
            - polygons
          select:
            - addr:housenumber
          where: 
            - building = 'yes'
            - amenity = 'parking'
        '''
        m = Mapping(y)
        self.assertTrue(m.themes[0].matches(GeomType.POLYGON,{'building':'yes'}))
        self.assertTrue(m.themes[0].matches(GeomType.POLYGON,{'amenity':'parking'}))

    def test_nonlist_matcher(self):
        y = '''
        buildings:
          types:
            - polygons
          select:
            - addr:housenumber
          where: building = 'yes'
        '''
        m = Mapping(y)
        self.assertTrue(m.themes[0].matches(GeomType.POLYGON,{'building':'yes'}))

    def test_gt(self):
        y = '''
        buildings:
          types:
            - polygons
          select:
            - building
          where: height > 20
        '''
        m = Mapping(y)
        self.assertTrue(m.themes[0].matches(GeomType.POLYGON,{'height':21}))
        self.assertFalse(m.themes[0].matches(GeomType.POLYGON,{'height':20}))

    def test_default_osm_id(self):
        y = '''
        buildings:
          types:
            - polygons
          select:
            - building
        '''
        m = Mapping(y)
        self.assertTrue(m.themes[0].osm_id)
        self.assertFalse('osm_id' in m.themes[0].keys)
        m = Mapping(y,default_osm_id=False)
        self.assertFalse(m.themes[0].osm_id)

    def test_osm_id_override(self):
        y = '''
        buildings:
          types:
            - polygons
          select:
            - building
            - osm_id
        '''
        m = Mapping(y)
        self.assertTrue(m.themes[0].osm_id)
        self.assertFalse('osm_id' in m.themes[0].keys)
        m = Mapping(y,default_osm_id=False)
        self.assertTrue(m.themes[0].osm_id)
        self.assertFalse('osm_id' in m.themes[0].keys)

    def test_duplicate_key(self):
        y = '''
        buildings:
          types:
            - polygons
          select:
            - building
            - building
        '''
        m = Mapping(y)
        self.assertTrue(len(m.themes[0].keys) == 1)

