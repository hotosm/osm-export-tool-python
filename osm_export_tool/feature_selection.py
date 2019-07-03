import os
import re
import yaml
import unicodedata
from yaml.constructor import ConstructorError
from yaml.scanner import ScannerError
from yaml.parser import ParserError
from osm_export_tool.sql import SQLValidator, OverpassFilter

def slugify(s):
    """
    Turn theme names into snake case slugs.
    adapted from https://github.com/django/django/blob/92053acbb9160862c3e743a99ed8ccff8d4f8fd6/django/utils/text.py#L417
    """
    slug = unicodedata.normalize('NFKD', s)
    #slug = slug.encode('ascii', 'ignore').lower()
    slug = re.sub(r'[^a-z0-9]+', '_', slug).strip('_')
    slug = re.sub(r'[_]+', '_', slug)
    return slug


class FeatureSelection(object):
    """ A feature selection object:
    """

    def __init__(self,raw_doc):
        self._raw_doc = raw_doc
        self._doc = None
        self._errors = []
        self.keys_from_sql = {}

    @property
    def doc(self):
        """ Validate when the YAML doc is accessed."""

        def validate_schema(loaded_doc):
            if not loaded_doc:
                self._errors.append("YAML cannot be empty")
                return False
            if not isinstance(loaded_doc,dict):
                self._errors.append("YAML must be dict, not list")
                return False
            for theme, theme_dict in loaded_doc.items():
                if not re.match('(?u)^[\w\s]+$', theme):
                    self._errors.append("Each theme must be named using only characters, numbers, underscores and spaces")
                    return False
                if not theme_dict or 'select' not in theme_dict:
                    self._errors.append("Each theme must have a 'select' key")
                    return False
                if 'types' in theme_dict:
                    for typ in theme_dict['types']:
                        if typ not in ['points','lines','polygons']:
                            self._errors.append("types must be one or more of points, lines or polygons, got: {0}".format(typ))
                            return False
                seen_tags = []
                if not theme_dict['select']:
                    self._errors.append("'select' cannot be empty")
                    return False
                for key in theme_dict['select']:
                    if not key:
                        self._errors.append("Missing OSM key")
                        return False
                    if key in seen_tags:
                        self._errors.append("Duplicate tag: {0}".format(key))
                        return False
                    seen_tags.append(key)
                if not isinstance(theme_dict['select'],list):
                    self._errors.append("'select' children must be list elements (e.g. '- amenity')")
                    return False

                self.keys_from_sql[theme] = set()
                if 'where' in theme_dict:
                    if not theme_dict['where']:
                        self._errors.append("if 'where' key is specified, it must not be empty")
                        return False
                    if not isinstance(theme_dict['where'],list):
                        clauses = [theme_dict['where']]
                    else:
                        clauses = theme_dict['where']
                    for clause in clauses:
                        s = SQLValidator(clause)
                        if not s.valid:
                            self._errors.append("SQL (" + clause + ') is invalid: ' + ' '.join(s.errors))
                            return False

                        # also add the keys to keys_from_sql
                        for k in s.column_names:
                            self.keys_from_sql[theme].add(k)

            return True

        if self._doc:
            return self._doc
        try:
            loaded_doc = yaml.safe_load(self._raw_doc)
            if validate_schema(loaded_doc):
                self._doc = loaded_doc
                return self._doc
        except (ConstructorError,ScannerError,ParserError) as e:
            line = e.problem_mark.line
            column = e.problem_mark.column
            #print e.problem_mark.buffer
            #print e.problem
            self._errors.append(e.problem)
            # add exceptions
            #self._valid = (self._yaml != None)

    def match(self,tags,geom_type):
        if len(tags) > 0:
            return ['buildings']
        return []


    @property
    def valid(self):
        return self.doc != None

    @property
    def errors(self):
        return self._errors

    @property
    def themes(self):
        if self.doc:
            return list(self.doc.keys())
        return []

    @property
    def slug_themes(self):
        return list(map(lambda x: slugify(x), self.themes))

    def geom_types(self,theme):
        if 'types' in self.doc[theme]:
            return self.doc[theme]['types']
        return ['points','lines','polygons']

    def key_selections(self,theme):
        return self.doc[theme]['select']

    def __str__(self):
        return str(self.doc)

    def key_union(self,geom_type=None):
        s = set()
        for t in self.themes:
            if geom_type == None or (geom_type in self.geom_types(t)):
                for key in self.key_selections(t):
                    s.add(key)
                for key in self.keys_from_sql[t]:
                    s.add(key)
        return sorted(list(s))

    @property
    def tables(self):
        retval = []
        for theme in self.themes:
            for geom_type in self.geom_types(theme):
                retval.append(slugify(theme) + '_' + geom_type)
        return retval


