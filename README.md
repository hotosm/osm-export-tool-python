# OSM Export Tool

> This project is under development. For the previous version of the Export Tool, see [hotosm/osm-export-tool](https://github.com/hotosm/osm-export-tool/tree/master/ops).

## Example usage

```
osm-export-tool jakarta.osm.pbf jakarta -f gpkg,shp
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
