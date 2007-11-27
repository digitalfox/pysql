#!/bin/sh
~/src/svn2cl-0.7/svn2cl.sh --group-by-day file:///home/fox/prog/depot/trunk/pysql/
~/src/svn2cl-0.7/svn2cl.sh --html --group-by-day file:///home/fox/prog/depot/trunk/pysql/
svn -m "Changelog update" commit ChangeLog ChangeLog.html
