#!/usr/bin/env bash
set -ev

DIR="$(dirname "$(readlink -f "$0")")"
COMPOSE_FILE="$DIR/../docker/docker-compose.yml"

docker-compose -f "$COMPOSE_FILE" build