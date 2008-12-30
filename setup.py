#!/usr/bin/python
# -*- coding: utf-8 -*-

"""Setup script used to build and install Pysql

@author: Sébastien Renard (sebastien.renard@digitalfox.org)
@license:GNU GPL V3
"""

from distutils.core import setup
import sys
from os.path import dirname, join

# Languages
langs=["fr"]
data_files=[]
for lang in langs:
    data_files.append(["share/locale/%s/LC_MESSAGES/" % lang, 
                       ["src/share/locale/%s/LC_MESSAGES/pysql.mo" % lang]])

# Additional files
data_files.append(["share/pysql",
                   ["version", "README", "ChangeLog", "ChangeLog-Synthesis", "LICENSE"]])

# Scripts
scripts=["src/bin/pysql"]

# Version
try:
    version=file(join(dirname(__file__), "version")).readline().rstrip().rstrip("\n")
except Exception, e:
    print "Warning, cannot read version file (%s)" % e
    print "Defaulting to 'snapshot'"
    version="snaphot"

# Windows post install script
if "win" in " ".join(sys.argv[1:]):
    scripts.append("pysql_w32_postinst.py")

#Go for setup 
setup(name="pysql",
      version=version,
      description="PySQL is an Oracle enhanced client",
      author="Sebastien Renard and Sebastien Delcros",
      author_email="pysql@digitalfox.org",
      url="http://pysql.sf.net",
      package_dir={"pysql" : "src/pysql"},
      packages=["pysql"],
      scripts=scripts,
      data_files=data_files
      )