import setuptools
import subprocess
import os

with open("README.md", "r") as fh:
    long_description = fh.read()

requirements = [
    'osmium~=2.15',
    'pyparsing~=2.4',
    'pyyaml',
    'shapely~=1.6'
]

if 'GDAL_VERSION' in os.environ:
    gdal_version = os.environ['GDAL_VERSION']
else:
    gdal_config = os.environ.get('GDAL_CONFIG', 'gdal-config')
    gdal_version = subprocess.check_output([gdal_config,'--version'],encoding='UTF-8').strip()

requirements.append(['gdal~=' + gdal_version])

setuptools.setup(
    name="osm-export-tool",
    version="0.0.4",
    author="Brandon Liu",
    author_email="brandon.liu@hotosm.org",
    description="Convert OpenStreetMap data into GIS and mobile mapping file formats.",
    license="BSD-3-Clause",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/hotosm/osm-export-tool-python",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
    ],
    scripts=['bin/osm-export-tool'],
    install_requires = requirements,
    requires_python='>=3.0',
)