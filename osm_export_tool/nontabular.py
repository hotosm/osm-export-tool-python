import os
from os.path import join
import pathlib
import subprocess

class Osmand:
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

    def __init__(self,input_pbf,map_creator_dir,tempdir=None,jvm_mem=[256,2048]):
        self.input_pbf = input_pbf
        self.tempdir = tempdir
        self.jvm_mem = jvm_mem
        self.map_creator_dir = map_creator_dir

    def run(self):
        pathlib.Path(join(self.tempdir,'osmand')).mkdir(parents=True, exist_ok=True)

        try:
            os.link(self.input_pbf,join(self.tempdir,'osmand','osmand.osm.pbf'))
        except:
            pass

        with open(join(self.tempdir,'batch.xml'),'w') as b:
            b.write(self.BATCH_XML.format(tempdir=self.tempdir))

        subprocess.check_call([
            'java',
            '-Xms{0}M'.format(self.jvm_mem[0]),
            '-Xmx{0}M'.format(self.jvm_mem[1]),
            '-cp',
            self.CLASSPATH.format(map_creator_dir=self.map_creator_dir),
            'net.osmand.util.IndexBatchCreator',
            join(self.tempdir,'batch.xml')
        ])

class Garmin:
    """
    Converts PBF to Garmin IMG format.

    Splits pbf into smaller tiles, generates .img files for each split,
    then patches the .img files back into a single .img file
    suitable for deployment to a Garmin GPS unit.
    """
    def __init__(self,input_pbf,splitter_jar,mkgmap_jar,tempdir=None,jvm_mem=[256,2048]):
        self.input_pbf = input_pbf
        self.splitter_jar = splitter_jar
        self.mkgmap_jar = mkgmap_jar
        self.tempdir = tempdir
        self.jvm_mem = jvm_mem

    def run(self):
        # NOTE: disabled poly bounds: see https://github.com/hotosm/osm-export-tool2/issues/248
        subprocess.check_call([
            'java',
            '-Xms{0}M'.format(self.jvm_mem[0]),
            '-Xmx{0}M'.format(self.jvm_mem[1]),
            '-jar',
            self.splitter_jar,
            '--output-dir=' + self.tempdir,
            self.input_pbf
        ])

        # Generate the IMG file.
        # get the template.args file created by splitter
        # see: http://wiki.openstreetmap.org/wiki/Mkgmap/help/splitter
        subprocess.check_call([
            'java',
            '-Xms{0}M'.format(self.jvm_mem[0]),
            '-Xmx{0}M'.format(self.jvm_mem[1]),
            '-jar',
            self.mkgmap_jar,
            '--gmapsupp',
            '--output-dir=' + self.tempdir,
            '--description="HOT Export Garmin Map"',
            '--mapname=80000111',
            '--family-name="HOT Export Tool"',
            '--family-id="2"',
            '--series-name="HOT Export Tool"',
            '--index',
            '--route',
            '--generate-sea=extend-sea-sectors',
            '--draw-priority=100',
            '--read-config={0}/template.args'.format(self.tempdir)
        ])

class Mwm:
    def __init__(self,input_pbf,generate_mwm_path,tempdir=None):
        self.input_pbf = input_pbf
        self.generate_mwm_path = generate_mwm_path

    def run(self):
        subprocess.check_call([
            self.generate_mwm_path,
            self.input_pbf
        ])

