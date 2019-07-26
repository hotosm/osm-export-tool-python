# OSM Export Tool

> This project is under development. For the previous version of the Export Tool, see [hotosm/osm-export-tool](https://github.com/hotosm/osm-export-tool/tree/master/ops).

## Motivation

This program filters and transforms OpenStreetMap data into thematic, tabular GIS formats. 
Filters are specified via YAML and a familiar SQL syntax, for example:
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

This program uses PyOsmium to read OSM files and GDAL/OGR to write GIS formats, so it should be reasonably fast and light on memory. There is also a OSM driver available for GDAL/OGR, but this program is intended to allow for more flexibility in the conversion process. it can also create files in non-tabular formats such as those for Garmin GPS devices or the OSMAnd Android app.

## Example usage

```
osm-export-tool jakarta.osm.pbf jakarta

-m : specify a mapping YAML. Defaults to example/defaults.yaml, which is a very broad selection of OSM tags.
-f : a comma-separated list of formats such as gpkg, shp. Defaults to just gpkg. 
```

Input formats:
* OSM PBF
* OSM XML

Output formats:
* OSM PBF
* OSM XML
* GeoPackage
* Shapefile
* KML
* OsmAnd
* Maps.ME
* Garmin

1. OGC GeoPackage (.gpkg)
* This is the default export format, and the most flexible for modern GIS applications. 

2. Shapefile (.shp)
* Each layer and geometry type is a separate .SHP file. This is because each .SHP file only supports a single geometry type and column schema. 

3. KML (.kml)
* Each layer and geometry type is a separate .KML file. This is because the GDAL/OGR KML driver does not support interleaved writing of features with different geometry types. 

4. Maps.ME

5. OsmAnd

6. Garmin
