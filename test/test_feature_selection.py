import unittest
from osm_export_tool.feature_selection.feature_selection import FeatureSelection

class TestFeatureSelection(unittest.TestCase):
    def test_empty_feature_selection(self):
        y = '''
        '''
        f = FeatureSelection(y)
        self.assertFalse(f.valid)

    def test_theme_names(self):
        y = '''
        A Theme Name:
            select:
                - name
        '''
        f = FeatureSelection(y)
        self.assertTrue(f.valid)
        self.assertEqual(f.themes,["A Theme Name"])
        self.assertEqual(f.slug_themes,["a_theme_name"])

        u = u'''
        Å Theme Name:
            select:
                - name
        '''
        f = FeatureSelection(y)
        self.assertTrue(f.valid)
        self.assertEqual(f.themes,["A Theme Name"])
        self.assertEqual(f.slug_themes,["a_theme_name"])


    def test_key_union_and_filters(self):
        y = '''
        waterways:
            types: 
                - lines
                - polygons
            select:
                - name
                - waterway
        buildings:
            types:
                - points
                - lines
                - polygons
            select:
                - name
                - building
            where: building IS NOT NULL
        '''
        f = FeatureSelection(y)
        self.assertEqual(f.themes,['waterways','buildings'])
        self.assertEqual(f.geom_types('waterways'),['lines','polygons'])
        self.assertEqual(f.key_selections('waterways'),['name','waterway'])
        self.assertEqual(f.key_union(), ['building','name','waterway'])
        self.assertEqual(f.key_union('points'), ['building','name'])

    def test_sql_empty_list(self):
        y = '''
        waterways:
            types:
                - polygons
            select:
                - name
            where: []
        '''
        f = FeatureSelection(y)
        self.assertFalse(f.valid)
        self.assertEqual(f.errors[0],"if 'where' key is specified, it must not be empty")

        y = '''
        waterways:
            types:
                - polygons
            select:
                - name
            where:
        '''
        f = FeatureSelection(y)
        self.assertFalse(f.valid)
        self.assertEqual(f.errors[0],"if 'where' key is specified, it must not be empty")

    def test_unsafe_yaml(self):
        y = '''
        !!python/object:feature_selection.feature_selection.FeatureSelection
        a: 0
        '''
        f = FeatureSelection(y)
        self.assertFalse(f.valid)
        self.assertEqual(1,len(f.errors))

    def test_malformed_yaml(self):
        # if it's not a valid YAML document
        # TODO: errors for if yaml indentation is incorrect
        y = '''
        all
            select:
                - name
        '''
        f = FeatureSelection(y)
        self.assertFalse(f.valid)

    def test_empty_yaml(self):
        y = '''
        {}
        '''
        f = FeatureSelection(y)
        self.assertFalse(f.valid)
        self.assertEqual(f.errors[0],"YAML cannot be empty")

    def test_minimal_yaml(self):
        # the shortest valid feature selection
        y = '''
        all: 
            select:
                - name
        '''
        f = FeatureSelection(y)
        self.assertTrue(f.valid)
        self.assertEqual(f.geom_types('all'),['points','lines','polygons'])

    def test_duplicated_yaml(self):
        y = '''
        all: 
            select:
                - name
                - name
        '''
        f = FeatureSelection(y)
        self.assertFalse(f.valid)
        self.assertEqual(f.errors[0],"Duplicate tag: name")
        y = '''
        t1: 
            select:
                - name
        t2: 
            select:
                - name

        '''
        f = FeatureSelection(y)
        self.assertTrue(f.valid)

    def test_unspecified_yaml(self):
        # top level is a list and not a dict
        y = '''
        - all: 
            select:
                - name
        '''
        f = FeatureSelection(y)
        self.assertFalse(f.valid)
        self.assertEqual(f.errors[0],"YAML must be dict, not list")

    def test_dash_spacing_yaml(self):
        # top level is a list and not a dict
        y = '''
        all: 
          select:
            -name
        '''
        f = FeatureSelection(y)
        self.assertFalse(f.valid)

    def test_no_select_yaml(self):
        # top level is a list and not a dict
        y = '''
        all: 
          -select:
            - name
        '''
        f = FeatureSelection(y)
        self.assertFalse(f.valid)
        self.assertEqual(f.errors[0],"Each theme must have a 'select' key")

        y = '''
        theme_0:
        '''
        f = FeatureSelection(y)
        self.assertFalse(f.valid)
        self.assertEqual(f.errors[0],"Each theme must have a 'select' key")

        y = '''
        theme_0:
            select:
        '''
        f = FeatureSelection(y)
        self.assertFalse(f.valid)
        self.assertEqual(f.errors[0],"'select' cannot be empty")

    def test_invalid_type(self):
        y = '''
        all: 
          types:
            - multilines
          select:
            - name
        '''
        f = FeatureSelection(y)
        self.assertFalse(f.valid)
        self.assertEqual(f.errors[0],"types must be one or more of points, lines or polygons, got: multilines")

    # refer to https://taginfo.openstreetmap.org/keys
    def test_valid_invalid_key_yaml(self):
        y = '''
        all: 
          select:
            - has space
            - has_underscore
            - has:colon
            - UPPERCASE
        '''
        f = FeatureSelection(y)
        self.assertTrue(f.valid)
        y = '''
        all: 
          select:
            - na?me
        '''
        f = FeatureSelection(y)
        self.assertTrue(f.valid)
        y = '''
        all: 
          select:
            -
        '''
        f = FeatureSelection(y)
        self.assertFalse(f.valid)
        self.assertEqual(f.errors[0],"Missing OSM key")

    def test_unicode_osm_key(self):
        # https://taginfo.openstreetmap.org/reports/characters_in_keys
        y = '''
planet_osm_polygon:
  types:
    - polygons
  select:
    - building￼Buildings
    '''
        f = FeatureSelection(y)
        self.assertTrue(f.valid)


    def test_passes_sqlvalidator_errors(self):
        y = '''
        buildings:
            select:
                - name
                - addr:housenumber
            where: addr:housenumber IS NOT NULL
        '''
        f = FeatureSelection(y)
        self.assertFalse(f.valid)
        self.assertEqual(f.errors[0], "SQL (addr:housenumber IS NOT NULL) is invalid: identifier with colon : must be in double quotes.")

    def test_enforces_subset_columns(self):
        y = '''
        buildings:
            types:
                - polygons
            select:
                - column1 
            where: column2 IS NOT NULL
        other:
            types:
                - points
            select:
                - column3
        '''
        f = FeatureSelection(y)
        self.assertTrue(f.valid)
        self.assertEqual(f.key_union(), ['column1','column2','column3'])
        self.assertEqual(f.key_union('points'), ['column3'])
