import os

class Osmand:
	BATCH_XML = """<?xml version="1.0" encoding="utf-8"?>
		<batch_process>
			<process_attributes mapZooms="" renderingTypesFile="" zoomWaySmoothness=""
				osmDbDialect="sqlite" mapDbDialect="sqlite"/>
			 <!-- zoomWaySmoothness - 1-4, typical mapZooms - 11;12;13-14;15-   -->
			<process directory_for_osm_files="{work_dir}/osmand"
		             directory_for_index_files="{work_dir}"
		             directory_for_generation="{work_dir}"
		             skipExistingIndexesAt="{work_dir}"
		             indexPOI="true"
		             indexRouting="true"
		             indexMap="true"
		             indexTransport="true"
		             indexAddress="true">
			</process>
		</batch_process>
		"""

	def __init__(self,input_pbf):
		pass

	def run(self):
		print(self.BATCH_XML)
		os.link(self.input_pbf,self.work_dir+"/osmand/osmand.osm.pbf")