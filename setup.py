import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="osm-export-tool",
    version="0.0.3",
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
    scripts=['bin/osm-export-tool']
)