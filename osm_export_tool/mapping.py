import yaml
import pyparsing
from osm_export_tool import GeomType
from osm_export_tool.sql import Matcher

class InvalidMapping(Exception):
	pass

class Theme:
	def __init__(self,name,d,default_osm_id):
		self.name = name

		# set geometry types.
		self.points = False
		self.lines = False
		self.polygons = False

		if not isinstance(d,dict):
			if isinstance(d,list):
				raise InvalidMapping('theme {0} must be YAML dict (types: , select:) , not list (- types, - select)'.format(name))
			raise InvalidMapping('Theme value must be dict')

		if 'types' not in d:
			self.points = True
			self.lines = True
			self.polygons = True
		else:
			for t in d['types']:
				if t not in ['points','lines','polygons']:
					raise InvalidMapping('types: for theme {0} must be list containing one or more of: points, lines, polygons'.format(name))
			if 'points' in d['types']:
				self.points = True
			if 'lines' in d['types']:
				self.lines = True
			if 'polygons' in d['types']:
				self.polygons = True


		if 'select' not in d:
			raise InvalidMapping('missing select: for theme {0}'.format(name))
		self.keys = set(d['select'])

		self.osm_id = default_osm_id
		if 'osm_id' in self.keys:
			self.osm_id = True
			self.keys.remove('osm_id')

		if 'where' in d:
			try:
				if not d['where']:
					raise InvalidMapping('where: for theme {0} is invalid'.format(name))
				if isinstance(d['where'],list):
					self.matcher = Matcher.null()
					for w in d['where']:
						self.matcher = self.matcher.union(Matcher.from_sql(w))
				else:
					self.matcher = Matcher.from_sql(d['where'])
			except pyparsing.ParseException:
				raise InvalidMapping('Invalid SQL: {0}'.format(d['where']))
		else:
			self.matcher = Matcher.null()
			for key in self.keys:
				self.matcher = self.matcher.union(Matcher.any(key))

		extra = d.copy()
		if 'where' in extra:
			del extra['where']
		if 'select' in d:
			del extra['select']
		if 'types' in d:
			del extra['types']
		self.extra = extra

	def matches(self,geom_type,tags):
		if geom_type == GeomType.POINT and not self.points:
			return False
		if geom_type == GeomType.LINE and not self.lines:
			return False
		if geom_type == GeomType.POLYGON and not self.polygons:
			return False

		return self.matcher.matches(tags)

	def __repr__(self):
		return self.name


class Mapping:
	def __init__(self,y,default_osm_id=True):
		doc = yaml.safe_load(y)

		if not isinstance(doc,dict):
			raise InvalidMapping('YAML must be dict')

		self.themes = []
		for theme_name, theme_dict in doc.items():
			self.themes.append(Theme(theme_name,theme_dict,default_osm_id=default_osm_id))

	@classmethod
	def validate(cls,y,**kwargs):
		try:
			return cls(y,kwargs), None
		except (yaml.scanner.ScannerError, yaml.parser.ParserError, InvalidMapping) as se:
			errors = [str(se)]
			return None, errors

