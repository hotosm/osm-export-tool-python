import os
import shutil
import subprocess
import requests
from string import Template

# path must return a path to an .osm.pbf or .osm.xml on the filesystem

class File:
    def __init__(self,path):
        self._path = path

    def path(self):
        return self._path

class Overpass:
    # TODO optimize for tags via feature selection
    def __init__(self,hostname,geom,path,use_existing=True,tempdir=None,osmconvert_path='osmconvert'):
        self.hostname = hostname
        self._path = path
        self.geom = geom
        self.use_existing = use_existing
        self.osmconvert_path = osmconvert_path
        self.tmp_path = 'tmp.osm.xml'

    def fetch(self):
        basic_template = Template('[maxsize:$maxsize][timeout:$timeout];$query;out meta;')
        query_template = Template('(node($geom);<;>>;>;)')

        if self.geom.geom_type == 'Polygon':
            geom = 'poly:"{0}"'.format(' '.join(['{1} {0}'.format(*x) for x in self.geom.exterior.coords]))
        else:
            bounds = self.geom.bounds
            west = max(bounds[0], -180)
            south = max(bounds[1], -90)
            east = min(bounds[2], 180)
            north = min(bounds[3], 90)
            geom = '{1},{0},{3},{2}'.format(west, south, east, north)

        query = query_template.substitute(geom=geom)
        data = basic_template.substitute(maxsize=21474848,timeout=1600,query=query)

        with requests.post(os.path.join(self.hostname,'api','interpreter'),data=data, stream=True) as r:
            with open(self.tmp_path, 'wb') as f:
                shutil.copyfileobj(r.raw, f)

        with open(self.tmp_path,'r') as f:
            sample = [next(f) for x in range(2)]
            if 'DOCTYPE html' in sample[1]:
                raise Exception('Overpass failure')

        # run osmconvert on the file
        subprocess.check_call([self.osmconvert_path,self.tmp_path,'--out-pbf','-o='+self._path])

    def path(self):
        if os.path.isfile(self._path) and self.use_existing:
            return self._path
        else:
            self.fetch()
        return self._path

class OsmiumSource:
    pass

