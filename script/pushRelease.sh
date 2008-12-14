#!/bin/sh
# Push release file to sf.net
rsync -avP -e ssh $* srenard@frs.sourceforge.net:uploads/
