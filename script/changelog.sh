#!/bin/sh
cd $(dirname $0)/..
git --no-pager log > ChangeLog.tmp
cat ChangeLog.tmp PastChangeLog > ChangeLog
rm ChangeLog.tmp
