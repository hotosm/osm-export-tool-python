import zipfile

# a package is a ZIP containing a README, the boundary geoJSON and the data files.

def create_package(destination,files,mapping_for_readme=None,boundary_geom=None):
	# the created zipfile must end with only .zip (not .shp.zip) for the HDX preview to work.
	with zipfile.ZipFile(destination, 'w', zipfile.ZIP_DEFLATED, True) as z:
		pass


