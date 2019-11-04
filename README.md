# OSM Export Tool

This project is in a usable state on Linux and Mac. The current [Export Tool web service](https://export.hotosm.org) repository is at [hotosm/osm-export-tool](https://github.com/hotosm/osm-export-tool/tree/master/ops).

## Motivation

This program filters and transforms OpenStreetMap data into thematic, tabular GIS formats. 
Filtering of features is specified via SQL embedded in a YAML mapping file, for example:
```
buildings_with_addresses:  # creates a thematic layer called "buildings_with_addresses"
  types:
    - polygons
  select:
    - building
    - height
    - addr:housenumber
  where:
    - building = 'yes' and addr:housenumber IS NOT NULL
```

It can also create files in non-tabular formats such as those for Garmin GPS devices or the OSMAnd Android app. (coming soon)

## Installation

* install via `pip install osm-export-tool`. Python 3 and a working GDAL installation are required. GDAL can be installed via Homebrew on Mac or the `ubuntugis` PPAs on Ubuntu.

PyOsmium is used to read OSM files and GDAL/OGR is used to write GIS files, so this program should be reasonably fast and light on memory. There is a built-in OSM reader available for GDAL/OGR, but this program is much more flexible.

This library will not automatically install GDAL because it needs to match the version on your system. You will need to separately run `pip install GDAL==2.3.2` (change 2.3.2 to match `gdalinfo --version`)

## Example usage

```
osm-export-tool INPUT_FILE.pbf OUTPUT_NAME
```
will create OUTPUT_NAME.gpkg.

All the below flags are optional.

* -m, --mapping : specify a mapping YAML. Defaults to `osm_export_tool/mappings/defaults.yaml`, which is a very broad selection of OSM tags ported from the [imposm3 defaults](https://github.com/omniscale/imposm3/blob/master/example-mapping.yml).
* `-f, --formats` : a comma-separated list of formats such as `gpkg,shp`. Defaults to just gpkg. 
* `--omit-osm-ids`: By default, every table will have an `osm_id` column. Relation IDs are negative. 
* `--clip <file>`: either a .poly or GeoJSON file.
	* The GeoJSON must be either a Polygon or MultiPolygon geometry, or a FeatureCollection with one Polygon or MultiPolygon feature.
	* Clipping is performed by Shapely and can be slow. It is recommended to filter the input PBF with a tool like [osmium-tool](https://github.com/osmcode/osmium-tool).

## YAML Mapping

* SQL statements must be comparisons of keys to constants with the key first.
	* Valid examples:
		* `height > 20`
		* `amenity='parking' OR (building = 'yes' and height > 5)`
	* Invalid examples:
		* `20 < height`
		* `building > height`
* More examples can be found in the [mappings directory](osm_export_tool/mappings).
* if the `types` key is omitted, it defaults to `points`, `lines` and `polygons`.
* At least one tag is required as a child of the `select` key.
* If the `where` key is omitted, it defaults to choosing all features where any of the `select`ed keys are present.
* if `where` is a list of SQL, it is equivalent to joining each SQL in the list with `OR`.

## Output formats

1. OGC GeoPackage (gpkg)
* This is the default export format, and the most flexible for modern GIS applications. 
* tables will be created with the wkbUnknown geometry type, which allows heterogeneous geometry types.

2. Shapefile (shp)
* Each layer and geometry type is a separate .SHP file. This is because each .SHP file only supports a single geometry type and column schema. 

3. KML (kml)
* Each layer and geometry type is a separate .KML file. This is because the GDAL/OGR KML driver does not support interleaved writing of features with different geometry types. 

4. Maps.ME (coming soon)

5. OsmAnd (coming soon)

6. Garmin (coming soon)
