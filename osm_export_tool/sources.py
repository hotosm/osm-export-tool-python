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
    def __init__(self,hostname,geom,path,use_existing=True):
        self.hostname = hostname
        self._path = path
        self.geom = geom
        self.use_existing = use_existing

    def fetch(self):
        # TODO find the hull of a MultiPolygon
        basic_template = Template('[maxsize:$maxsize][timeout:$timeout];$query;out meta;')
        query_template = Template('(node($geom);<;>>;>;)')

        poly = 'poly:"{0}"'.format(' '.join(['{1} {0}'.format(*x) for x in self.geom.exterior.coords]))
        query = query_template.substitute(geom=poly)
        data = basic_template.substitute(maxsize=21474848,timeout=1600,query=query)

        with requests.post(os.path.join(self.hostname,'api','interpreter'),data=data, stream=True) as r:
            with open(self._path, 'wb') as f:
                shutil.copyfileobj(r.raw, f)

    def path(self):
        if os.path.isfile(self._path) and self.use_existing:
            return self._path
        else:
            self.fetch()
        return self._path

class OsmiumSource:
    pass

