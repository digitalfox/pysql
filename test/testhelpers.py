# -*- coding: utf-8 -*-

"""common test functions
@author: Sébastien Renard (sebastien.renard@digitalfox.org)
@license:GNU GPL V3
"""

import gettext
import sys
import os
from os.path import abspath, dirname, join, pardir
from tempfile import TemporaryFile

def setup():
    # Set  PYDEVDEBUG to 1 in order to desactivate shell colors
    os.environ["PYDEVDEBUG"]="1"

    # Setup gettext to avoid error with the global _() function
    gettext.install("pysql", "", unicode=1)

    # Add pysql module path
    sys.path.append(abspath(join(dirname(__file__), pardir, "src", "pysql")))

    # Set locale
    # Loads config (first time)
    from pysqlconf import PysqlConf
    conf=PysqlConf.getConfig()

    # Sets the locale
    import pysqlmain
    pysqlmain.setLocale(conf)

class CapturedStdout:
    """Capture sys.out output in temp file to allow function result testing
    Thanks to Catherine Devlin (catherinedevlin.blogspot.com) for the idea"""

    def __init__(self):
        """Capture stdout"""
        self.backupStdout=sys.stdout
        self.tmpFile=TemporaryFile()
        sys.stdout=self.tmpFile

    def readlines(self, reset=True):
        """
        @param reset: reset buffer for next usage (default is True)
        @return: array of lines captured and reset buffer"""
        self.tmpFile.seek(0)
        lines=self.tmpFile.readlines()
        if reset:
            self.reset()
        return [line.strip("\n").strip("\x00") for line in lines]

    def reset(self):
        """Reset stdout buffer"""
        self.tmpFile.truncate(0)

    def gotPsyqlException(self, reset=True):
        """Look if captured output has a PysqlException
        @param reset: reset buffer for next usage (default is True)
        @return: True is got exception, else False"""
        lines=self.readlines(reset)
        for line in lines:
            if "Pysql error" in line:
                return True
        return False

    def echoStdout(self):
        """Echo the current buffer on terminal stdout. Usefull for test debuging"""
        self.backupStdout.writelines(["%s\n" % line for line in self.readlines(reset=False)])

    def restoreStdout(self):
        sys.stdout=self.backupStdout
        self.tmpFile.close()
