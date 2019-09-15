import unittest
from osm_export_tool.sources import Overpass
from osm_export_tool.mapping import Mapping

class TestMappingToOverpass(unittest.TestCase):
    def test_mapping(self):
        y = '''
        buildings:
            types:
                - points
            select:
                - column1 
            where: column2 IS NOT NULL

        other1:
            types:
                - points
                - polygons
            select:
                - column1 
                - irrelevant
            where: column2 IS NOT NULL AND column3 IN ('foo','bar')

        other2:
            types:
                - lines
            select:
                - column5:key
        '''
        mapping = Mapping(y)
        nodes, ways, relations = Overpass.filters(mapping)
        self.assertCountEqual(nodes,["['column3'~'foo|bar']","['column2']"])
        # force quoting of strings to handle keys with colons
        self.assertCountEqual(ways,["['column5:key']","['column3'~'foo|bar']","['column2']"])
        self.assertCountEqual(relations,["['column3'~'foo|bar']","['column2']"])

class TestSQLToOverpass(unittest.TestCase):
    def test_basic(self):
        s = Overpass.sql("name = 'somename'")
        self.assertEqual(s,["['name'='somename']"])
        s = Overpass.sql("level > 4")
        self.assertEqual(s,["['level']"])

    def test_basic_list(self):
        s = Overpass.sql("name IN ('val1','val2')")
        self.assertEqual(s,["['name'~'val1|val2']"])

    def test_whitespace(self):
        s = Overpass.sql("name = 'some value'")
        self.assertEqual(s,["['name'='some value']"])

    def test_notnull(self):
        s = Overpass.sql("name is not null")
        self.assertEqual(s,["['name']"])

    def test_and_or(self):
        s = Overpass.sql("name1 = 'foo' or name2 = 'bar'")
        self.assertEqual(s,["['name1'='foo']","['name2'='bar']"])
        s = Overpass.sql("(name1 = 'foo' and name2 = 'bar') or name3 = 'baz'")
        self.assertEqual(s,["['name1'='foo']","['name2'='bar']","['name3'='baz']"])