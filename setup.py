#!/usr/bin/python
# -*- coding: utf-8 -*-

# Sébastien Renard (sebastien.renard@digitalfox.org)
# Code licensed under GNU GPL V2

from distutils.core import setup
import sys

# Languages
langs=["fr"]
data_files=[]
for lang in langs:
    data_files.append(["share/locale/%s/LC_MESSAGES/" % lang, 
                       ["locale/%s/LC_MESSAGES/pysql.mo" % lang]])

# Scripts
scripts=["src/bin/pysql"]

# Windows post install script
if "win" in " ".join(sys.argv[1:]):
    scripts.append("pysql_w32_postinst.py")

#Go for setup 
setup(name="pysql",
      version="0.12",
      description="PySQL is an Oracle enhanced client",
      author="Sebastien Renard and Sebastien Delcros",
      author_email="pysql@digitalfox.org",
      url="http://pysql.sf.net",
      package_dir={"pysql" : "src/pysql"},
      packages=["pysql"],
      scripts=scripts,
      data_files=data_files
      )