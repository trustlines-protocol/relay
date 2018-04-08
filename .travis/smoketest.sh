#!/usr/bin/env bash
set -ev
DIR="$(dirname "$(readlink -f "$0")")"
COMPOSE_FILE="$DIR/../docker/docker-compose.yml"
TEST_FILE="$DIR/../smoketest/smoketest.py"

cat docker/addresses.json
docker-compose -f "$COMPOSE_FILE" pull
docker-compose -f "$COMPOSE_FILE" build
docker-compose -f "$COMPOSE_FILE" start
sleep 60
docker-compose -f "$COMPOSE_FILE" ps
docker-compose -f "$COMPOSE_FILE" logs | cat
cat docker/addresses.json
python -m pytest $TEST_FILE
docker-compose -f "$COMPOSE_FILE" down
