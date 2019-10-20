import os
from enum import Enum
# force loading of shapely before ogr, see https://github.com/Toblerity/Shapely/issues/490
from shapely.geometry import shape, MultiPolygon, Polygon

name = 'osm_export_tool'

class GeomType(Enum):
    POINT = 1
    LINE = 2
    POLYGON = 3

def GetHumanReadable(size,precision=2):
    suffixes=['B','KB','MB','GB','TB']
    suffixIndex = 0
    while size > 1024 and suffixIndex < 4:
        suffixIndex += 1 #increment the index of the suffix
        size = size/1024.0 #apply the division
    return "%.*f%s"%(precision,size,suffixes[suffixIndex])

# can be more than one file (example: Shapefile w/ sidecars)
class File:
    def __init__(self,output_name,parts,extra = {}):
        self.output_name = output_name
        self.parts = parts
        self.extra = extra

    @classmethod
    def shp(cls,name,extra = {}):
        parts = [name + '.shp']
        parts.append(name + '.shx')
        parts.append(name + '.prj')
        parts.append(name + '.cpg')
        parts.append(name + '.dbf')
        return cls('shp',parts,extra)

    def size(self):
        total = 0
        for part in self.parts:
            total = total + os.path.getsize(part)
        return total

    def __str__(self):
        return '{0} {1} {2} {3}'.format(self.output_name,self.extra,','.join(self.parts),GetHumanReadable(self.size()))

    def __repr__(self):
        return self.__str__()