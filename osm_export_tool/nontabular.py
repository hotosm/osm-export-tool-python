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

    def __init__(self,input_pbf,tempdir=None):
        self.input_pbf = input_pbf
        self.tempdir = tempdir

    def run(self):
        pathlib.Path(join(self.tempdir,'osmand')).mkdir(parents=True, exist_ok=True)

        try:
            os.link(self.input_pbf,join(self.tempdir,"/osmand/osmand.osm.pbf"))
        except:
            pass

        with open(join(self.tempdir,'batch.xml'),'w') as b:
            b.write(self.BATCH_XML.format(tempdir=self.tempdir))

        subprocess.check_call([
            'java',
            '-cp',
            self.CLASSPATH.format(map_creator_dir='tools/OsmAndMapCreator-main'),
            'net.osmand.util.IndexBatchCreator',
            join(self.tempdir,'batch.xml')
        ])
