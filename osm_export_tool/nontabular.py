import os
from os.path import join
import pathlib
import subprocess
from osm_export_tool import File
import landez

def osmand(input_pbf,map_creator_dir,tempdir=None,jvm_mem=[256,2048]):
    BATCH_XML = """<?xml version="1.0" encoding="utf-8"?>
        <batch_process>
            <process_attributes mapZooms="" renderingTypesFile="" zoomWaySmoothness=""
                osmDbDialect="sqlite" mapDbDialect="sqlite"/>
             <!-- zoomWaySmoothness - 1-4, typical mapZooms - 11;12;13-14;15-   -->
            <process directory_for_osm_files="{tempdir}/osmand"
                     directory_for_index_files="{tempdir}"
                     directory_for_generation="{tempdir}"
                     skipExistingIndexesAt="{tempdir}"
                     indexPOI="true"
                     indexRouting="true"
                     indexMap="true"
                     indexTransport="true"
                     indexAddress="true">
            </process>
        </batch_process>
        """
    CLASSPATH = "{map_creator_dir}/OsmAndMapCreator.jar:{map_creator_dir}/lib/OsmAnd-core.jar:{map_creator_dir}/lib/*.jar"

    pathlib.Path(join(tempdir,'osmand')).mkdir(parents=True, exist_ok=True)

    try:
        os.link(input_pbf,join(tempdir,'osmand','osmand.osm.pbf'))
    except:
        pass

    with open(join(tempdir,'batch.xml'),'w') as b:
        b.write(BATCH_XML.format(tempdir=tempdir))

    subprocess.check_call([
        'java',
        '-Xms{0}M'.format(jvm_mem[0]),
        '-Xmx{0}M'.format(jvm_mem[1]),
        '-cp',
        CLASSPATH.format(map_creator_dir=map_creator_dir),
        'net.osmand.util.IndexBatchCreator',
        join(tempdir,'batch.xml')
    ])
    return [File('osmand_obf',[join(tempdir,'Osmand_2.obf')])]

def garmin(input_pbf,splitter_jar,mkgmap_jar,tempdir=None,jvm_mem=[256,2048]):
    """
    Converts PBF to Garmin IMG format.

    Splits pbf into smaller tiles, generates .img files for each split,
    then patches the .img files back into a single .img file
    suitable for deployment to a Garmin GPS unit.
    NOTE: disabled poly bounds: see https://github.com/hotosm/osm-export-tool2/issues/248
    """
    subprocess.check_call([
        'java',
        '-Xms{0}M'.format(jvm_mem[0]),
        '-Xmx{0}M'.format(jvm_mem[1]),
        '-jar',
        splitter_jar,
        '--output-dir=' + tempdir,
        input_pbf
    ])

    # Generate the IMG file.
    # get the template.args file created by splitter
    # see: http://wiki.openstreetmap.org/wiki/Mkgmap/help/splitter
    subprocess.check_call([
        'java',
        '-Xms{0}M'.format(jvm_mem[0]),
        '-Xmx{0}M'.format(jvm_mem[1]),
        '-jar',
        mkgmap_jar,
        '--gmapsupp',
        '--output-dir=' + tempdir,
        '--description="HOT Export Garmin Map"',
        '--mapname=80000111',
        '--family-name="HOT Export Tool"',
        '--family-id="2"',
        '--series-name="HOT Export Tool"',
        '--index',
        '--route',
        '--generate-sea=extend-sea-sectors',
        '--draw-priority=100',
        '--read-config={0}/template.args'.format(tempdir)
    ])
    return [File('garmin',[join(tempdir,'gmapsupp.img')])]

def mwm(input_pbf,output_dir,generate_mwm_path,generator_tool_path,osmconvert_path='osmconvert'):
    base_name = (os.path.basename(input_pbf).split(os.extsep))[0]
    env = os.environ.copy()
    env.update(OSMCONVERT=osmconvert_path,TARGET=output_dir,GENERATOR_TOOL=generator_tool_path)
    subprocess.check_call([
        generate_mwm_path,
        input_pbf
    ],env=env)
    return [File('mwm',[join(output_dir,base_name + '.mwm')])]

def mbtiles(geom,filepath,tiles_url,minzoom,maxzoom):
    mb = landez.MBTilesBuilder(cache=False,tiles_url=tiles_url,tiles_headers={'User-Agent':'github.com/hotosm/osm-export-tool'},filepath=filepath)
    mb.add_coverage(bbox=geom.bounds,
                    zoomlevels=[minzoom,maxzoom])
    mb.run()
    return [File('mbtiles',[filepath],{'minzoom':minzoom,'maxzoom':maxzoom,'source':tiles_url})]
