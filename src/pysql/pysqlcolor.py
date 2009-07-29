#!/usr/bin/python
# -*- coding: utf-8 -*-

"""ANSI terminal color code
@author: Sébastien Renard (sebastien.renard@digitalfox.org)
@license:GNU GPL V3
"""

# Python imports:
import os

if os.name=='posix' and os.getenv("PYDEVDEBUG", "0")=="0":
    BOLD    = '\033[01m'
    RED     = '\033[31m'
    GREEN   = '\033[32m'
    ORANGE  = '\033[33m'
    BLUE    = '\033[34m'
    PURPLE  = '\033[35m'
    CYAN    = '\033[36m'
    GREY    = '\033[37m'
    RESET   = '\033[0;0m'
else:
    BOLD    = ''
    RED     = ''
    GREEN   = ''
    ORANGE  = ''
    BLUE    = ''
    PURPLE  = ''
    CYAN    = ''
    GREY    = ''
    RESET   = ''