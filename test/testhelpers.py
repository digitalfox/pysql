# -*- coding: utf-8 -*-

"""common test functions
@author: Sébastien Renard (sebastien.renard@digitalfox.org)
@license:GNU GPL V3
"""

import gettext
import sys
from os.path import abspath, dirname, join, pardir

def setup():
    # Setup gettext to avoid error with the global _() function
    gettext.install("pysql", "", unicode=1)

    # Add pysql module path
    sys.path.append(abspath(join(dirname(__file__), pardir, "src", "pysql")))
