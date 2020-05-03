FROM debian:buster-slim

RUN apt-get update && apt-get install -yq \
    python3-pip \
    python3-gdal

RUN pip3 install \
    osm-export-tool

COPY bin/docker_entrypoint.sh /bin/docker_entrypoint.sh

ENTRYPOINT [ "/bin/docker_entrypoint.sh" ]
