import os
import shutil
import subprocess
import requests
from string import Template
from osm_export_tool.sql import to_prefix

# path must return a path to an .osm.pbf or .osm.xml on the filesystem

class File:
    def __init__(self,path):
        self._path = path

    def path(self):
        return self._path

class Overpass:

    @classmethod
    def filters(cls,mapping):
        nodes = set()
        ways = set()
        relations = set()
        for t in mapping.themes:
            parts = cls.parts(t.matcher.expr)
            if t.points:
                for part in parts:
                    nodes.add(part)
            if t.lines:
                for part in parts:
                    ways.add(part)
            if t.polygons:
                for part in parts:
                    ways.add(part)
                    relations.add(part)
        return nodes,ways,relations

    # force quoting of strings to handle keys with colons
    @classmethod
    def parts(cls, expr):
        def _parts(prefix):
            op = prefix[0]
            if op == '=':
                return ["['{0}'='{1}']".format(prefix[1],prefix[2])]
            if op in ['<','>','<=','>='] or op == 'notnull':
                return ["['{0}']".format(prefix[1])]
            if op == 'in':
                x = "['{0}'~'{1}']".format(prefix[1],'|'.join(prefix[2]))
                return [x]
            if op == 'and' or op == 'or':
                return _parts(prefix[1]) + _parts(prefix[2])
        return _parts(expr)

    @classmethod
    def sql(cls,str):
        return cls.parts(to_prefix(str))

    def __init__(self,hostname,geom,path,use_existing=True,tempdir=None,osmconvert_path='osmconvert',mapping=None):
        self.hostname = hostname
        self._path = path
        self.geom = geom
        self.use_existing = use_existing
        self.osmconvert_path = osmconvert_path
        self.tmp_path = os.path.join(tempdir,'tmp.osm.xml')
        self.mapping = mapping

    def fetch(self):
        base_template = Template('[maxsize:$maxsize][timeout:$timeout];$query;out meta;')

        if self.geom.geom_type == 'Polygon':
            geom = 'poly:"{0}"'.format(' '.join(['{1} {0}'.format(*x) for x in self.geom.exterior.coords]))
        else:
            bounds = self.geom.bounds
            west = max(bounds[0], -180)
            south = max(bounds[1], -90)
            east = min(bounds[2], 180)
            north = min(bounds[3], 90)
            geom = '{1},{0},{3},{2}'.format(west, south, east, north)

        if self.mapping:
            query = """(
                (
                    {0}
                );
                (
                    {1}
                );>;
                (
                    {2}
                );>>;>;)"""
            nodes,ways,relations = Overpass.filters(self.mapping)
            nodes = '\n'.join(['node({0}){1};'.format(geom,f) for f in nodes])
            ways = '\n'.join(['way({0}){1};'.format(geom,f) for f in ways])
            relations = '\n'.join(['relation({0}){1};'.format(geom,f) for f in relations])
            query = query.format(nodes,ways,relations)
        else:
            query = '(node({0});<;>>;>;)'.format(geom)

        data = base_template.substitute(maxsize=21474848,timeout=1600,query=query)

        with requests.post(os.path.join(self.hostname,'api','interpreter'),data=data, stream=True) as r:
            with open(self.tmp_path, 'wb') as f:
                shutil.copyfileobj(r.raw, f)

        with open(self.tmp_path,'r') as f:
            sample = [next(f) for x in range(2)]
            if 'DOCTYPE html' in sample[1]:
                raise Exception('Overpass failure')

        # run osmconvert on the file
        subprocess.check_call([self.osmconvert_path,self.tmp_path,'--out-pbf','-o='+self._path])
        os.remove(self.tmp_path)

    def path(self):
        if os.path.isfile(self._path) and self.use_existing:
            return self._path
        else:
            self.fetch()
        return self._path

class OsmiumSource:
    pass

