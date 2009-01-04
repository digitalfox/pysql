#!/usr/bin/python
# -*- coding: utf-8 -*-

"""pysqlhelpers module test suite
@author: Sébastien Renard (sebastien.renard@digitalfox.org)
@license:GNU GPL V3
"""

import unittest
import sys

# Common test pysql tools
import testhelpers
testhelpers.setup()

# Pysql imports
import pysqlshell
from pysqlexception import PysqlException

global CONNECT_STRING
CONNECT_STRING=""

class TestConnectedShellCommands(unittest.TestCase):
    """All that test need an Oracle connection"""
    def setUp(self):
        if not CONNECT_STRING:
            self.fail("You must provide a connection string for connected tests")
        # Capture stdout - This must be done before shell init
        self.capturedStdout=testhelpers.CapturedStdout()
        self.shell=pysqlshell.PysqlShell(argv=[CONNECT_STRING,])
        self.shell.preloop() # Needed to populate command list (self.cmds)
        if not self.shell.db: 
            self.fail("No Oracle connection")
        self.capturedStdout.reset() # Remove shell init banner

    def tearDown(self):
        """Restore stdout"""
        self.capturedStdout.restoreStdout()
        
    def exeCmd(self, line):
        """Execute precmd, onecmd then postcmd shell method"""
        line=self.shell.precmd(line)
        stop=self.shell.onecmd(line)
        stop=self.shell.postcmd(stop, line)

    def test_do_bg(self):
        self.exeCmd("bg\n")
        self.assertEqual(self.capturedStdout.readlines(), ["(no result)"])
        
        self.exeCmd("bg 1")
        self.failUnless(self.capturedStdout.gotPsyqlException())
        
        self.exeCmd("select 'coucou' from dual&")
        self.assertEqual(self.capturedStdout.readlines(), ["Background query launched"])

        self.exeCmd("bg")
        self.exeCmd("bg 1")
        self.failIf(self.capturedStdout.gotPsyqlException())

        self.exeCmd("bg 1")
        self.failUnless(self.capturedStdout.gotPsyqlException())

if __name__ == '__main__':
    if len(sys.argv)>1:
        CONNECT_STRING=sys.argv.pop()
    else:
        CONNECT_STRING=""

    unittest.main()