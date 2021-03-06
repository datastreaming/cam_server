#!/bin/bash
VERSION=4.3.0
#docker image prune --all --filter "until=4320h"   #delete images older than 6 months
#docker system prune
docker build --no-cache=true -t paulscherrerinstitute/cam_server .
docker tag paulscherrerinstitute/cam_server paulscherrerinstitute/cam_server:$VERSION
docker login
docker push paulscherrerinstitute/cam_server:$VERSION
docker push paulscherrerinstitute/cam_server

