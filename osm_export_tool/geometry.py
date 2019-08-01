import json
from shapely.geometry import shape, MultiPolygon, Polygon

def parse_poly(lines):
    """ Parse an Osmosis polygon filter file.
        Accept a sequence of lines from a polygon file, return a shapely.geometry.MultiPolygon object.
        https://wiki.openstreetmap.org/wiki/Osmosis/Polygon_Filter_File_Python_Parsing
    """
    in_ring = False
    coords = []
    for (index, line) in enumerate(lines):
        if index == 0:
            # first line is junk.
            continue
        elif index == 1:
            # second line is the first polygon ring.
            coords.append([[], []])
            ring = coords[-1][0]
            in_ring = True
        elif in_ring and line.strip() == 'END':
            # we are at the end of a ring, perhaps with more to come.
            in_ring = False
        elif in_ring:
            # we are in a ring and picking up new coordinates.
            ring.append(list(map(float, line.split())))
        elif not in_ring and line.strip() == 'END':
            # we are at the end of the whole polygon.
            break
        elif not in_ring and line.startswith('!'):
            # we are at the start of a polygon part hole.
            coords[-1][1].append([])
            ring = coords[-1][1][-1]
            in_ring = True
        elif not in_ring:
            # we are at the start of a polygon part.
            coords.append([[], []])
            ring = coords[-1][0]
            in_ring = True
    
    return MultiPolygon(coords)

def load_geometry(txt):
	try:
		j = json.loads(txt)
		if j['type'] == 'FeatureCollection':
			print("Warning: using first feature of --clip FeatureCollection.")
			return shape(j['features'][0]['geometry'])
		else:
			return shape(j)
	except json.decoder.JSONDecodeError:
		pass
	return parse_poly(txt.split('\n'))
