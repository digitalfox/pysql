#!/bin/sh
# Push release file to sf.net
rsync -avP -e ssh $(dirname $0)/../dist/ srenard@frs.sourceforge.net:uploads/
