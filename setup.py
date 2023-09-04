import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

requirements = [
    "osmium~=3.5.0",
    "pyparsing~=2.4",
    "pyyaml",
    "shapely~=1.6",
    "requests>=2.22.0",
    "landez~=2.5.0",
]

setuptools.setup(
    name="osm-export-tool-python",
    version="2.0.8",
    author="Hot Tech Team",
    author_email="sysadmin@hotosm.org",
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
    scripts=["bin/osm-export-tool"],
    install_requires=requirements,
    requires_python=">=3.0",
    package_data={"osm_export_tool": ["mappings/*.yml"]},
)
