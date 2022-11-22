#!/usr/bin/env bash

CUSTOM_COMPILE_COMMAND="./compile-requirements" python -m piptools compile --output-file=requirements.txt constraints.in setup.py "${@}"
CUSTOM_COMPILE_COMMAND="./compile-requirements" python -m piptools compile dev-requirements.in "${@}"
