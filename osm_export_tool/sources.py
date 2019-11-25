import json
import os
import shutil
import subprocess
import requests
from string import Template
from osm_export_tool.sql import to_prefix
import shapely.geometry

# path must return a path to an .osm.pbf or .osm.xml on the filesystem

class Pbf:
    def __init__(self,path):
        self._path = path

    def fetch(self):
        pass

    def path(self):
        return self._path

class OsmExpress:
    def __init__(self,osmx_path,db_path,geom,output_path,use_existing=True,tempdir=None):
        self.osmx_path = osmx_path
        self.db_path = db_path
        self.geom = geom
        self.output_path = output_path
        self.use_existing = use_existing
        self.tempdir = tempdir

    def fetch(self):
        region_json = os.path.join(self.tempdir,'region.json')
        with open(region_json,'w') as f:
            f.write(json.dumps(shapely.geometry.mapping(self.geom)))
        subprocess.check_call([self.osmx_path,'extract',self.db_path,self.output_path,'--region',region_json])
        os.remove(region_json)

    def path(self):
        if os.path.isfile(self.output_path) and self.use_existing:
            return self.output_path
        else:
            self.fetch()
        return self.output_path

class OsmiumTool:
    def __init__(self,osmium_path,source_path,geom,output_path,use_existing=True,tempdir=None):
        self.osmium_path = osmium_path
        self.source_path = source_path
        self.geom = geom
        self.output_path = output_path
        self.use_existing = use_existing
        self.tempdir = tempdir

    def fetch(self):
        region_json = os.path.join(self.tempdir,'region.json')
        with open(region_json,'w') as f:
            f.write(json.dumps({'type':'Feature','geometry':shapely.geometry.mapping(self.geom)}))
        subprocess.check_call([self.osmium_path,'extract','-p',region_json,self.source_path,'-o',self.output_path,'--overwrite'])
        os.remove(region_json)

    def path(self):
        if os.path.isfile(self.output_path) and self.use_existing:
            return self.output_path
        else:
            self.fetch()
        return self.output_path

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
            if op == '!=':
                return ["['{0}'!='{1}']".format(prefix[1],prefix[2])]
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

    def __init__(self,hostname,geom,path,use_existing=True,tempdir=None,osmconvert_path='osmconvert',mapping=None,use_curl=False):
        self.hostname = hostname
        self._path = path
        self.geom = geom
        self.use_existing = use_existing
        self.osmconvert_path = osmconvert_path
        self.tmp_path = os.path.join(tempdir,'tmp.osm.xml')
        self.mapping = mapping
        self.use_curl = use_curl
        self.tempdir = tempdir

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

        data = base_template.substitute(maxsize=2147483648,timeout=1600,query=query)

        if self.use_curl:
            with open(os.path.join(self.tempdir,'query.txt'),'w') as query_txt:
                query_txt.write(data)
            print(['curl','-X','POST','-d','@'+os.path.join(self.tempdir,'query.txt'),os.path.join(self.hostname,'api','interpreter'),'-o',self.tmp_path])
            subprocess.check_call(['curl','-X','POST','-d','@'+os.path.join(self.tempdir,'query.txt'),os.path.join(self.hostname,'api','interpreter'),'-o',self.tmp_path])
        else:
            with requests.post(os.path.join(self.hostname,'api','interpreter'),data=data, stream=True) as r:
                with open(self.tmp_path, 'wb') as f:
                    shutil.copyfileobj(r.raw, f)

        with open(self.tmp_path,'r') as f:
            sample = [next(f) for x in range(6)]
            if 'DOCTYPE html' in sample[1]:
                raise Exception('Overpass failure')
            if 'remark' in sample[5]:
                raise Exception(sample[5])

        # run osmconvert on the file
        subprocess.check_call([self.osmconvert_path,self.tmp_path,'--out-pbf','-o='+self._path])
        os.remove(self.tmp_path)

    def path(self):
        if os.path.isfile(self._path) and self.use_existing:
            return self._path
        else:
            self.fetch()
        return self._path


