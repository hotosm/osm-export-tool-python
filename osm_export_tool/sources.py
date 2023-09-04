import json
import os
import pathlib
import shutil
import subprocess
import time
from sre_constants import SUCCESS
from string import Template
from xml.dom import ValidationErr

import requests
import shapely.geometry
from deepdiff import DeepDiff
from requests.exceptions import Timeout

from osm_export_tool.sql import to_prefix

# path must return a path to an .osm.pbf or .osm.xml on the filesystem
MAX_RETRIES = 5
RETRY_DELAY = 60


class Pbf:
    def __init__(self, path):
        self._path = path

    def fetch(self):
        pass

    def path(self):
        return self._path


class OsmExpress:
    def __init__(
        self, osmx_path, db_path, geom, output_path, use_existing=True, tempdir=None
    ):
        self.osmx_path = osmx_path
        self.db_path = db_path
        self.geom = geom
        self.output_path = output_path
        self.use_existing = use_existing
        self.tempdir = tempdir

    def fetch(self):
        region_json = os.path.join(self.tempdir, "region.json")
        with open(region_json, "w") as f:
            f.write(json.dumps(shapely.geometry.mapping(self.geom)))
        subprocess.check_call(
            [
                self.osmx_path,
                "extract",
                self.db_path,
                self.output_path,
                "--region",
                region_json,
            ]
        )
        os.remove(region_json)

    def path(self):
        if os.path.isfile(self.output_path) and self.use_existing:
            return self.output_path
        else:
            self.fetch()
        return self.output_path


class OsmiumTool:
    def __init__(
        self,
        osmium_path,
        source_path,
        geom,
        output_path,
        use_existing=True,
        tempdir=None,
        mapping=None,
    ):
        self.osmium_path = osmium_path
        self.source_path = source_path
        self.geom = geom
        self.output_path = output_path
        self.use_existing = use_existing
        self.tempdir = tempdir
        self.mapping = mapping

    @classmethod
    def parts(cls, expr):
        def _parts(prefix):
            op = prefix[0]
            if op == "=":
                return ["{0}={1}".format(prefix[1], prefix[2])]
            if op == "!=":
                return ["{0}!={1}".format(prefix[1], prefix[2])]
            if op in ["<", ">", "<=", ">="] or op == "notnull":
                raise ValueError("{0} where clause not supported".format(op))
            if op == "in":
                x = "{0}={1}".format(prefix[1], ",".join(prefix[2]))
                return [x]
            if op == "and" or op == "or":
                return _parts(prefix[1]) + _parts(prefix[2])

        return _parts(expr)

    @staticmethod
    def get_element_filter(theme, part):
        elements = []
        if theme.points:
            elements.append("n/{0}".format(part))  # node
        if theme.lines:
            elements.append("w/{0}".format(part))  # way
        if theme.polygons:
            elements.append("r/{0}".format(part))  # relation

        return elements

    @classmethod
    def filters(cls, mapping):
        filters_set = set()
        tags = set()
        for t in mapping.themes:
            prefix = t.matcher.expr
            parts = cls.parts(prefix)
            for part in parts:
                [filters_set.add(e) for e in OsmiumTool.get_element_filter(t, part)]
                key = [t for t in t.keys if t in part]
                if len(key) == 1:
                    tags.add(key[0])

        return filters_set

    def tags_filter(self, filters, planet_as_source):
        source_path = self.output_path
        if planet_as_source is True:
            source_path = self.source_path

        cmd = [self.osmium_path, "tags-filter", source_path, "-o", self.output_path]

        for f in filters:
            cmd.insert(3, f)

        if planet_as_source is False:
            cmd.append("--overwrite")

        subprocess.check_call(cmd)

    def fetch(self):
        region_json = os.path.join(self.tempdir, "region.json")
        with open(region_json, "w") as f:
            f.write(
                json.dumps(
                    {"type": "Feature", "geometry": shapely.geometry.mapping(self.geom)}
                )
            )
        subprocess.check_call(
            [
                self.osmium_path,
                "extract",
                "-p",
                region_json,
                self.source_path,
                "-o",
                self.output_path,
                "--overwrite",
            ]
        )
        os.remove(region_json)

    def path(self):
        if os.path.isfile(self.output_path) and self.use_existing:
            return self.output_path

        planet_as_source = True
        if self.geom.area < 6e4:
            self.fetch()
            planet_as_source = False

        if self.mapping is not None:
            filters = OsmiumTool.filters(self.mapping)
            self.tags_filter(filters, planet_as_source)

        return self.output_path


class Overpass:
    @classmethod
    def filters(cls, mapping):
        nodes = set()
        ways = set()
        relations = set()
        for t in mapping.themes:
            parts = cls.parts(t.matcher.expr)
            if t.points:
                for part in parts:
                    nodes.add(part)
            if t.lines:
                for part in parts:
                    ways.add(part)
            if t.polygons:
                for part in parts:
                    ways.add(part)
                    relations.add(part)
        return nodes, ways, relations

    # force quoting of strings to handle keys with colons
    @classmethod
    def parts(cls, expr):
        def _parts(prefix):
            op = prefix[0]
            if op == "=":
                return ["['{0}'='{1}']".format(prefix[1], prefix[2])]
            if op == "!=":
                return ["['{0}'!='{1}']".format(prefix[1], prefix[2])]
            if op in ["<", ">", "<=", ">="] or op == "notnull":
                return ["['{0}']".format(prefix[1])]
            if op == "in":
                x = "['{0}'~'{1}']".format(prefix[1], "|".join(prefix[2]))
                return [x]
            if op == "and" or op == "or":
                return _parts(prefix[1]) + _parts(prefix[2])

        return _parts(expr)

    @classmethod
    def sql(cls, str):
        return cls.parts(to_prefix(str))

    def __init__(
        self,
        hostname,
        geom,
        path,
        use_existing=True,
        tempdir=None,
        osmconvert_path="osmconvert",
        mapping=None,
        use_curl=False,
    ):
        self.hostname = hostname
        self._path = path
        self.geom = geom
        self.use_existing = use_existing
        self.osmconvert_path = osmconvert_path
        self.tmp_path = os.path.join(tempdir, "tmp.osm.xml")
        self.mapping = mapping
        self.use_curl = use_curl
        self.tempdir = tempdir

    def fetch(self):
        base_template = Template(
            "[maxsize:$maxsize][timeout:$timeout];$query;out meta;"
        )

        if self.geom.geom_type == "Polygon":
            geom = 'poly:"{0}"'.format(
                " ".join(["{1} {0}".format(*x) for x in self.geom.exterior.coords])
            )
        else:
            bounds = self.geom.bounds
            west = max(bounds[0], -180)
            south = max(bounds[1], -90)
            east = min(bounds[2], 180)
            north = min(bounds[3], 90)
            geom = "{1},{0},{3},{2}".format(west, south, east, north)

        if self.mapping:
            query = """(
                (
                    {0}
                );
                (
                    {1}
                );>;
                (
                    {2}
                );>>;>;)"""
            nodes, ways, relations = Overpass.filters(self.mapping)
            nodes = "\n".join(["node({0}){1};".format(geom, f) for f in nodes])
            ways = "\n".join(["way({0}){1};".format(geom, f) for f in ways])
            relations = "\n".join(
                ["relation({0}){1};".format(geom, f) for f in relations]
            )
            query = query.format(nodes, ways, relations)
        else:
            query = "(node({0});<;>>;>;)".format(geom)

        data = base_template.substitute(maxsize=2147483648, timeout=1600, query=query)

        if self.use_curl:
            with open(os.path.join(self.tempdir, "query.txt"), "w") as query_txt:
                query_txt.write(data)
            subprocess.check_call(
                [
                    "curl",
                    "-X",
                    "POST",
                    "-d",
                    "@" + os.path.join(self.tempdir, "query.txt"),
                    os.path.join(self.hostname, "api", "interpreter"),
                    "-o",
                    self.tmp_path,
                ]
            )
        else:
            with requests.post(
                os.path.join(self.hostname, "api", "interpreter"),
                data=data,
                stream=True,
            ) as r:
                with open(self.tmp_path, "wb") as f:
                    shutil.copyfileobj(r.raw, f)

        with open(self.tmp_path, "r") as f:
            sample = [next(f) for x in range(6)]
            if "DOCTYPE html" in sample[1]:
                raise Exception("Overpass failure")
            if "remark" in sample[5]:
                raise Exception(sample[5])
        # run osmconvert on the file
        try:
            subprocess.check_call(
                [self.osmconvert_path, self.tmp_path, "--out-pbf", "-o=" + self._path]
            )
        except subprocess.CalledProcessError as e:
            raise ValidationErr(e)
        os.remove(self.tmp_path)

    def path(self):
        if os.path.isfile(self._path) and self.use_existing:
            return self._path
        else:
            self.fetch()
        return self._path


class Galaxy:
    """Transfers Yaml Language to Galaxy Query Make a request and sends response back from fetch()"""

    @classmethod
    def hdx_filters(cls, t):
        geometryType = []
        or_filter, and_filter, point_filter, line_filter, poly_filter = (
            {},
            {},
            {},
            {},
            {},
        )
        point_columns, line_columns, poly_columns = [], [], []

        parts, and_clause = cls.parts(t.matcher.expr)
        if len(and_clause) > 0:
            ### FIX ME to support and clause with multiple condition
            temp_and_clause = []
            for clause in and_clause:
                for ause in clause:
                    temp_and_clause.append(ause)

            and_clause = temp_and_clause
            for cl in and_clause:
                if cl in parts:
                    parts.remove(cl)
            # -----
            and_filter = cls.remove_duplicates(
                cls.where_filter(temp_and_clause, and_filter)
            )

        or_filter = cls.remove_duplicates(cls.where_filter(parts, or_filter))
        if t.points:
            point_columns = cls.attribute_filter(t)
            geometryType.append("point")
            point_filter = {"join_or": or_filter, "join_and": and_filter}

        if t.lines:
            line_columns = cls.attribute_filter(t)
            geometryType.append("line")
            line_filter = {"join_or": or_filter, "join_and": and_filter}

        if t.polygons:
            poly_columns = cls.attribute_filter(t)
            geometryType.append("polygon")
            poly_filter = {"join_or": or_filter, "join_and": and_filter}

        return (
            point_filter,
            line_filter,
            poly_filter,
            geometryType,
            point_columns,
            line_columns,
            poly_columns,
        )

    @classmethod
    def filters(cls, mapping):
        geometryType = []
        or_filter, and_filter, point_filter, line_filter, poly_filter = (
            {},
            {},
            {},
            {},
            {},
        )
        point_columns, line_columns, poly_columns = [], [], []

        for t in mapping.themes:
            parts, and_clause = cls.parts(t.matcher.expr)

            if len(and_clause) > 0:
                ### FIX ME to support and clause with multiple condition
                temp_and_clause = []
                for clause in and_clause:
                    for ause in clause:
                        temp_and_clause.append(ause)

                and_clause = temp_and_clause
                for cl in and_clause:
                    if cl in parts:
                        parts.remove(cl)
                # -----
                and_filter = cls.remove_duplicates(
                    cls.where_filter(temp_and_clause, and_filter)
                )

            or_filter = cls.remove_duplicates(cls.where_filter(parts, or_filter))

            if t.points:
                point_columns = cls.attribute_filter(t)
                geometryType.append("point")
                point_filter = {"join_or": or_filter, "join_and": and_filter}

            if t.lines:
                line_columns = cls.attribute_filter(t)
                geometryType.append("line")
                line_filter = {"join_or": or_filter, "join_and": and_filter}

            if t.polygons:
                poly_columns = cls.attribute_filter(t)
                geometryType.append("polygon")
                poly_filter = {"join_or": or_filter, "join_and": and_filter}

        return (
            point_filter,
            line_filter,
            poly_filter,
            geometryType,
            point_columns,
            line_columns,
            poly_columns,
        )

    @classmethod
    def remove_duplicates(cls, entries_dict):
        for key, value in entries_dict.items():
            entries_dict[key] = list(dict.fromkeys(value))
        return entries_dict

    # force quoting of strings to handle keys with colons
    @classmethod
    def parts(cls, expr, and_clause=[]):
        def _parts(prefix):
            op = prefix[0]
            if op == "=":
                return [""" "{0}":["{1}"] """.format(prefix[1], prefix[2])]
            if (
                op == "!="
            ):  # fixme this will require improvement in rawdata api is not implemented yet
                pass
                # return ["['{0}'!='{1}']".format(prefix[1],prefix[2])]
            if op in ["<", ">", "<=", ">="] or op == "notnull":
                return [""" "{0}":[] """.format(prefix[1])]
            if op == "in":
                x = """ "{0}":["{1}"]""".format(prefix[1], """ "," """.join(prefix[2]))
                return [x]
            if op == "and":
                and_clause.append(_parts(prefix[1]) + _parts(prefix[2]))
                return _parts(prefix[1]) + _parts(prefix[2])
            if op == "or":
                return _parts(prefix[1]) + _parts(prefix[2])

        return _parts(expr), and_clause

    @classmethod
    def attribute_filter(cls, theme):
        columns = theme.keys
        return list(columns)

    @classmethod
    def where_filter(cls, parts, filter_dict):
        for part in parts:
            part_dict = json.loads(f"""{'{'}{part.strip()}{'}'}""")
            for key, value in part_dict.items():
                if key not in filter_dict:
                    filter_dict[key] = value
                else:
                    if (
                        filter_dict.get(key) != []
                    ):  # only add other values if not null condition is not applied to that key
                        if (
                            value == []
                        ):  # if incoming value is not null i.e. key = * ignore previously added values
                            filter_dict[key] = value
                        else:
                            filter_dict[
                                key
                            ] += value  # if value was not previously = * then and value is not =* then add values

        return filter_dict

    def __init__(self, hostname, geom, mapping=None, file_name=""):
        self.hostname = hostname
        self.geom = geom
        self.mapping = mapping
        self.file_name = file_name

    def fetch(self, output_format, is_hdx_export=False, all_feature_filter_json=None):
        if all_feature_filter_json:
            with open(all_feature_filter_json, encoding="utf-8") as all_features:
                all_features_filters = json.loads(all_features.read())
        geom = shapely.geometry.mapping(self.geom)

        if self.mapping:
            if is_hdx_export:
                # hdx block
                fullresponse = []
                for t in self.mapping.themes:
                    (
                        point_filter,
                        line_filter,
                        poly_filter,
                        geometryType_filter,
                        point_columns,
                        line_columns,
                        poly_columns,
                    ) = Galaxy.hdx_filters(t)
                    osmTags = point_filter
                    if point_filter == line_filter == poly_filter:
                        osmTags = point_filter  # master filter that will be applied to all type of osm elements : current implementation of galaxy api
                    else:
                        osmTags = {}
                    if point_columns == line_columns == poly_columns:
                        columns = point_columns
                    else:
                        columns = []
                    if len(geometryType_filter) == 0:
                        geometryType_filter = ["point", "line", "polygon"]

                    for geomtype in geometryType_filter:
                        geomtype_to_pass = [geomtype]
                        formatted_file_name = f"""{self.file_name.lower()}_{t.name.lower()}_{geomtype.lower()}s_{output_format.lower()}"""
                        if (
                            osmTags
                        ):  # if it is a master filter i.e. filter same for all type of feature
                            if columns:
                                request_body = {
                                    "fileName": formatted_file_name,
                                    "geometry": geom,
                                    "outputType": output_format,
                                    "geometryType": geomtype_to_pass,
                                    "filters": {
                                        "tags": {"all_geometry": osmTags},
                                        "attributes": {"all_geometry": columns},
                                    },
                                }
                            else:
                                request_body = {
                                    "fileName": formatted_file_name,
                                    "geometry": geom,
                                    "outputType": output_format,
                                    "geometryType": geomtype_to_pass,
                                    "filters": {
                                        "tags": {"all_geometry": osmTags},
                                        "attributes": {
                                            "point": point_columns,
                                            "line": line_columns,
                                            "polygon": poly_columns,
                                        },
                                    },
                                }
                        else:
                            if columns:
                                request_body = {
                                    "fileName": formatted_file_name,
                                    "geometry": geom,
                                    "outputType": output_format,
                                    "geometryType": geomtype_to_pass,
                                    "filters": {
                                        "tags": {
                                            "point": point_filter,
                                            "line": line_filter,
                                            "polygon": poly_filter,
                                        },
                                        "attributes": {"all_geometry": columns},
                                    },
                                }
                            else:
                                request_body = {
                                    "fileName": formatted_file_name,
                                    "geometry": geom,
                                    "outputType": output_format,
                                    "geometryType": geomtype_to_pass,
                                    "filters": {
                                        "tags": {
                                            "point": point_filter,
                                            "line": line_filter,
                                            "polygon": poly_filter,
                                        },
                                        "attributes": {
                                            "point": point_columns,
                                            "line": line_columns,
                                            "polygon": poly_columns,
                                        },
                                    },
                                }
                        # sending post request and saving response as response object
                        headers = {
                            "accept": "application/json",
                            "Content-Type": "application/json",
                        }
                        # print(request_body)
                        try:
                            if all_feature_filter_json:
                                if (
                                    len(
                                        DeepDiff(
                                            request_body["filters"],
                                            all_features_filters,
                                            ignore_order=True,
                                        )
                                    )
                                    < 1
                                ):  # that means user is selecting all the options available on export tool
                                    request_body["filters"] = {}

                            with requests.Session() as req_session:
                                # print("printing before sending")
                                # print(json.dumps(request_body))
                                for retry in range(MAX_RETRIES):
                                    r = req_session.post(
                                        url=f"{self.hostname}v1/snapshot/",
                                        data=json.dumps(request_body),
                                        headers=headers,
                                        timeout=60 * 5,
                                    )

                                    if r.status_code == 429:  # Rate limited
                                        print(
                                            f"Rate limited, retrying in {RETRY_DELAY} seconds..."
                                        )
                                        time.sleep(RETRY_DELAY)
                                    elif r.status_code != 200:  # Unexpected status code
                                        if r.status_code == 422:  # Unprocessable Entity
                                            try:
                                                error_message = r.json().get("detail")[
                                                    0
                                                ]["msg"]
                                            except (
                                                json.JSONDecodeError,
                                                KeyError,
                                                IndexError,
                                            ):
                                                error_message = "Unknown error occurred"
                                            raise ValueError(
                                                f"Error {r.status_code}: {error_message}"
                                            )
                                        else:
                                            r.raise_for_status()  # Raise other non-200 errors
                                    else:  # Success
                                        break
                                if r.ok:
                                    res = r.json()
                                else:
                                    raise ValueError(r.content)
                            url = f"{self.hostname}v1{res['track_link']}"
                            success = False
                            while not success:
                                with requests.Session() as api:
                                    r = api.get(url)
                                    r.raise_for_status()
                                    if r.ok:
                                        res = r.json()
                                        if res["status"] == "FAILURE":
                                            raise ValueError(
                                                "Task failed from export tool api"
                                            )
                                        if res["status"] == "SUCCESS":
                                            success = True
                                            response_back = res["result"]
                                            response_back["theme"] = t.name
                                            response_back["output_name"] = output_format
                                            fullresponse.append(response_back)
                                            time.sleep(
                                                0.5
                                            )  # wait one half sec before making another request
                                        else:
                                            time.sleep(2)  # Check every 2s for hdx

                        except requests.exceptions.RequestException as ex:
                            raise ex

                return fullresponse
            else:
                (
                    point_filter,
                    line_filter,
                    poly_filter,
                    geometryType_filter,
                    point_columns,
                    line_columns,
                    poly_columns,
                ) = Galaxy.filters(self.mapping)
                osmTags = point_filter
                if point_filter == line_filter == poly_filter:
                    osmTags = point_filter  # master filter that will be applied to all type of osm elements : current implementation of galaxy api
                else:
                    osmTags = {}
                if point_columns == line_columns == poly_columns:
                    columns = point_columns
                else:
                    columns = []

                if (
                    osmTags
                ):  # if it is a master filter i.e. filter same for all type of feature
                    attribute_meta = (
                        {"all_geometry": columns}
                        if columns
                        else {
                            "point": point_columns,
                            "line": line_columns,
                            "polygon": poly_columns,
                        }
                    )

                    request_body = {
                        "fileName": self.file_name,
                        "geometry": geom,
                        "outputType": output_format,
                        "geometryType": geometryType_filter,
                        "filters": {
                            "tags": {"all_geometry": osmTags},
                            "attributes": attribute_meta,
                        },
                    }
                else:
                    if columns:
                        request_body = {
                            "fileName": self.file_name,
                            "geometry": geom,
                            "outputType": output_format,
                            "geometryType": geometryType_filter,
                            "filters": {
                                "tags": {
                                    "point": point_filter,
                                    "line": line_filter,
                                    "polygon": poly_filter,
                                },
                                "attributes": {"all_geometry": columns},
                            },
                        }
                    else:
                        request_body = {
                            "fileName": self.file_name,
                            "geometry": geom,
                            "outputType": output_format,
                            "geometryType": geometryType_filter,
                            "filters": {
                                "tags": {
                                    "point": point_filter,
                                    "line": line_filter,
                                    "polygon": poly_filter,
                                },
                                "attributes": {
                                    "point": point_columns,
                                    "line": line_columns,
                                    "polygon": poly_columns,
                                },
                            },
                        }

                if all_feature_filter_json:
                    if (
                        len(
                            DeepDiff(
                                request_body["filters"],
                                all_features_filters,
                                ignore_order=True,
                            )
                        )
                        < 1
                    ):  # that means user is selecting all the options available on export tool
                        request_body["filters"] = {}

        else:
            request_body = {
                "fileName": self.file_name,
                "geometry": geom,
                "outputType": output_format,
            }

        headers = {"accept": "application/json", "Content-Type": "application/json"}
        # print(request_body)
        try:
            with requests.Session() as req_session:
                # print("printing before sending")
                # print(json.dumps(request_body))
                for retry in range(MAX_RETRIES):
                    r = req_session.post(
                        url=f"{self.hostname}v1/snapshot/",
                        data=json.dumps(request_body),
                        headers=headers,
                        timeout=60 * 5,
                    )

                    if r.status_code == 429:  # Rate limited
                        print(f"Rate limited, retrying in {RETRY_DELAY} seconds...")
                        time.sleep(RETRY_DELAY)
                    elif r.status_code != 200:  # Unexpected status code
                        print(json.dumps(request_body))
                        r.raise_for_status()
                    else:  # Success
                        break
                if r.ok:
                    res = r.json()
                else:
                    raise ValueError(r.content)
            url = f"{self.hostname}v1{res['track_link']}"
            success = False
            while not success:
                with requests.Session() as api:
                    r = api.get(url)
                    r.raise_for_status()
                    if r.ok:
                        res = r.json()
                        if res["status"] == "FAILURE":
                            raise ValueError("Task failed from export tool api")
                        if res["status"] == "SUCCESS":
                            success = True
                            return [res["result"]]
                        else:
                            time.sleep(1)  # Check each 1 seconds

        except requests.exceptions.RequestException as ex:
            raise ex
