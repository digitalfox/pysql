#!/usr/bin/python
# -*- coding: utf-8 -*-

"""pysqlhelpers module test suite
@author: Sébastien Renard (sebastien.renard@digitalfox.org)
@license:GNU GPL V3
"""

import unittest
import os
import sys

# Common test pysql tools
import testhelpers
testhelpers.setup()

# Pysql imports
import pysqlshell
from pysqlexception import PysqlException

global CONNECT_STRING
CONNECT_STRING=""

class TestShellCommands(unittest.TestCase):
    """Mother class of all shell tests.
    This class only defines common shell test method"""
    def setUp(self):
        # Capture stdout - This must be done before shell init
        self.capturedStdout=testhelpers.CapturedStdout()
        self.shell=pysqlshell.PysqlShell(argv=[CONNECT_STRING,])
        self.shell.preloop() # Needed to populate command list (self.cmds)

    def exeCmd(self, line):
        """Execute precmd, onecmd then postcmd shell method"""
        line=self.shell.precmd(line)
        stop=self.shell.onecmd(line)
        stop=self.shell.postcmd(stop, line)

    def lastExceptionOraCode(self):
        """@return: Oracle error code of last exception or None if last exceptions was not an Oracle one or
        no exception occurs at all"""
        if len(self.shell.exceptions)==0:
            return None
        lastException=self.shell.exceptions[-1]
        if lastException.oraCode:
            return lastException.oraCode
        else:
            return None

    def tearDown(self):
        """Restore stdout"""
        self.capturedStdout.restoreStdout()


class TestConnectedShellCommands(TestShellCommands):
    """Test commands that need an Oracle connection"""
    def setUp(self):
        TestShellCommands.setUp(self) # Father constructor
        if not CONNECT_STRING:
            self.fail("You must provide a connection string for connected tests")
        if not self.shell.db: 
            self.fail("No Oracle connection")
        self.capturedStdout.reset() # Remove shell init banner

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

    def test_do_connect(self):
        self.exeCmd("connect")
        self.failUnless(self.capturedStdout.gotPsyqlException())

        self.exeCmd("connect %s" % CONNECT_STRING)
        self.failIf(self.capturedStdout.gotPsyqlException())

        self.exeCmd("connect %s as sysdba" % CONNECT_STRING)
        self.failIf(self.capturedStdout.gotPsyqlException(reset=False))
        self.failUnless("as" in self.capturedStdout.readlines()[0])

        self.exeCmd("connect %s sysdba" % CONNECT_STRING)
        if self.capturedStdout.gotPsyqlException() and self.lastExceptionOraCode()!="ORA-01031":
            self.fail("Cannot connect as sysdba or bad ORA code")

    def test_do_disconnect(self):
        self.exeCmd("disconnect")
        self.failIf(self.capturedStdout.gotPsyqlException())
        # Reconnect for other tests
        self.exeCmd("connect %s" % CONNECT_STRING)
        self.failIf(self.capturedStdout.gotPsyqlException())


class TestNotConnectedShellCommands(TestShellCommands):
    """Tests for all commands that do not need an Oracle connection"""
    def test_do_showCompletion(self):
        self.exeCmd("showCompletion")
        self.failIf(self.capturedStdout.gotPsyqlException())

    def test_do_history(self):
        try:
            import readline
            # This will match the next command position
            position=readline.get_current_history_length()
        except Exception, e:
            position=""
            if os.name=="posix":
                self.fail("Cannot use readline: %s" % e)

        for cmd in ("history", "history %s" % position):
            self.exeCmd(cmd)
            self.failIf(self.capturedStdout.gotPsyqlException())

        for cmd in ("history a", "history -1", "history 10.5", "history 10,5", "history 2 4"):
            self.exeCmd(cmd)
            self.failUnless(self.capturedStdout.gotPsyqlException())


class TestCompleters(unittest.TestCase):
    """Tests for command completers"""
    pass


if __name__ == '__main__':
    if len(sys.argv)>1:
        CONNECT_STRING=sys.argv.pop()
    else:
        CONNECT_STRING=""

    unittest.main()