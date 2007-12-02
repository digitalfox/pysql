#!/bin/sh
~/src/svn2cl-0.7/svn2cl.sh --group-by-day https://pysql.svn.sourceforge.net/svnroot/pysql/trunk/pysql
#~/src/svn2cl-0.7/svn2cl.sh --group-by-day file:///home/fox/prog/depot/trunk/pysql/
#~/src/svn2cl-0.7/svn2cl.sh --html --group-by-day file:///home/fox/prog/depot/trunk/pysql/
#~/src/svn2cl-0.7/svn2cl.sh --html --group-by-day https://pysql.svn.sourceforge.net/svnroot/pysql/trunk/pysql
cat ChangeLog PastChangeLog > ChangeLog.tmp
mv ChangeLog.tmp ChangeLog
echo svn -m "Changelog update" commit ChangeLog www/ChangeLog.html
