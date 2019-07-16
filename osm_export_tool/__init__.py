name = 'osm_export_tool'

from enum import Enum

class GeomType(Enum):
    POINT = 1
    LINE = 2
    POLYGON = 3