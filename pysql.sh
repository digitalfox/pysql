#!/bin/sh
# Sebastien Renard - 2007
# License: GPL v3

# Simple shell wrapper to launch pysql from source package
# This is intended only for developpers or users that don't want to "install" pysql
# but just use it from a simple directory

# Tell python where to find packages
export PYTHONPATH=$(dirname $0)/src

# Start it
exec $(dirname $0)/src/bin/pysql $*
