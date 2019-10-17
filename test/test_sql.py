import unittest
from osm_export_tool.sql import SQLValidator, Matcher

class TestSql(unittest.TestCase):

    def test_basic(self):
        s = SQLValidator("name = 'a name'")
        self.assertTrue(s.valid)

    def test_identifier_list(self):
        s = SQLValidator("natural in ('water','cliff')")
        self.assertTrue(s.valid)

    def test_float_value(self):
        s = SQLValidator("height > 20")
        self.assertTrue(s.valid)

    def test_not_null(self):
        s = SQLValidator("height IS NOT NULL")
        self.assertTrue(s.valid)

    def test_and_or(self):
        s = SQLValidator("height IS NOT NULL and height > 20")
        self.assertTrue(s.valid)
        s = SQLValidator("height IS NOT NULL or height > 20")
        self.assertTrue(s.valid)
        s = SQLValidator("height IS NOT NULL or height > 20 and height < 30")
        self.assertTrue(s.valid)

    def test_parens(self):
        s = SQLValidator("(admin IS NOT NULL and level > 4)")
        self.assertTrue(s.valid)
        s = SQLValidator("(admin IS NOT NULL and level > 4) AND height is not null")
        self.assertTrue(s.valid)

    def test_colons_etc(self):
        s = SQLValidator("addr:housenumber IS NOT NULL")
        self.assertTrue(s.valid)
        s = SQLValidator("admin_level IS NOT NULL")
        self.assertTrue(s.valid)

    def test_invalid_sql(self):
        s = SQLValidator("drop table planet_osm_polygon")
        self.assertFalse(s.valid)
        self.assertEqual(s.errors,['SQL could not be parsed.'])
        s = SQLValidator("(drop table planet_osm_polygon)")
        self.assertFalse(s.valid)
        self.assertEqual(s.errors,['SQL could not be parsed.'])
        s = SQLValidator ("")
        self.assertFalse(s.valid)
        self.assertEqual(s.errors,['SQL could not be parsed.'])
        s = SQLValidator("name = 'a name'; blah")
        self.assertFalse(s.valid)
        self.assertEqual(s.errors,['SQL could not be parsed.'])

    def test_column_names(self):
        s = SQLValidator("(admin IS NOT NULL and level > 4) AND height is not null")
        self.assertTrue(s.valid)
        self.assertEqual(s.column_names,['admin','level','height'])

class TestMatcher(unittest.TestCase):
    def test_matcher_binop(self):
        m = Matcher.from_sql("building = 'yes'")
        self.assertTrue(m.matches({'building':'yes'}))
        self.assertFalse(m.matches({'building':'no'}))

        m = Matcher.from_sql("building != 'yes'")
        self.assertFalse(m.matches({'building':'yes'}))
        self.assertTrue(m.matches({'building':'no'}))

    def test_matcher_colon(self):
        m = Matcher.from_sql("addr:housenumber = 1")
        self.assertTrue(m.matches({'addr:housenumber':'1'}))

        m = Matcher.from_sql("building != 'yes'")
        self.assertFalse(m.matches({'building':'yes'}))
        self.assertTrue(m.matches({'building':'no'}))

    def test_matcher_doublequote(self):
        m = Matcher.from_sql("\"addr:housenumber\" = 1")
        self.assertTrue(m.matches({'addr:housenumber':'1'}))

        m = Matcher.from_sql("\"addr:housenumber\" IN ('foo')")
        self.assertTrue(m.matches({'addr:housenumber':'foo'}))

        m = Matcher.from_sql("\"addr:housenumber\" IS NOT NULL")
        self.assertTrue(m.matches({'addr:housenumber':'foo'}))

    def test_matcher_or(self):
        m = Matcher.from_sql("building = 'yes' OR amenity = 'bank'")
        self.assertTrue(m.matches({'building':'yes'}))
        self.assertTrue(m.matches({'amenity':'bank'}))
        self.assertFalse(m.matches({}))

    def test_matcher_and(self):
        m = Matcher.from_sql("building = 'yes' AND amenity = 'bank'")
        self.assertFalse(m.matches({'building':'yes'}))
        self.assertFalse(m.matches({'amenity':'bank'}))

    def test_matcher_is_not_null(self):
        m = Matcher.from_sql("building IS NOT NULL")
        self.assertTrue(m.matches({'building':'one'}))
        self.assertTrue(m.matches({'building':'two'}))
        self.assertFalse(m.matches({}))

    def test_in(self):
        m = Matcher.from_sql("building IN ('one','two')")
        self.assertTrue(m.matches({'building':'one'}))
        self.assertTrue(m.matches({'building':'two'}))
        self.assertFalse(m.matches({}))
        self.assertFalse(m.matches({'building':'three'}))

    def test_any(self):
        m = Matcher.any("building");
        self.assertTrue(m.matches({'building':'one'}))

    def test_union(self):
        m = Matcher.any("building").union(Matcher.any("parking"))
        self.assertTrue(m.matches({'building':'one'}))
        self.assertTrue(m.matches({'parking':'one'}))

    def test_null(self):
        m = Matcher.null()
        self.assertFalse(m.matches({'building':'one'}))

    def test_to_sql(self):
        sql = "building = 'yes'"
        self.assertEqual(Matcher.from_sql(sql).to_sql(),sql)
        sql = "building IS NOT NULL"
        self.assertEqual(Matcher.from_sql(sql).to_sql(),sql)
        sql = "building IN ('one','two')"
        self.assertEqual(Matcher.from_sql(sql).to_sql(),sql)
        sql = "building != 'yes'"
        self.assertEqual(Matcher.from_sql(sql).to_sql(),sql)
        sql = "building >= 0"
        self.assertEqual(Matcher.from_sql(sql).to_sql(),sql)
        sql = "building <= 0"
        self.assertEqual(Matcher.from_sql(sql).to_sql(),sql)
        sql = "building > 0"
        self.assertEqual(Matcher.from_sql(sql).to_sql(),sql)
        sql = "building < 0"
        self.assertEqual(Matcher.from_sql(sql).to_sql(),sql)
        sql = "building > 0 AND building < 5"
        self.assertEqual(Matcher.from_sql(sql).to_sql(),sql)
        sql = "building > 0 OR building < 5"
        self.assertEqual(Matcher.from_sql(sql).to_sql(),sql)
