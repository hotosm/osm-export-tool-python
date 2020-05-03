#!/usr/bin/env bash

set -e

mkdir -p /work
cd /work
osm-export-tool "$@"
