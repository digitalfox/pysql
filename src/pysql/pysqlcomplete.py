#!/usr/bin/python
# -*- coding: utf-8 -*-

""" This module defines complete terms gathering stuff
@author: Sébastien Renard (sebastien.renard@digitalfox.org)
@license: GNU GPL V3
"""

# pylint: disable-msg=E1101

# Python imports:
import os, re, time
from threading import Thread

# Pysql imports:
from pysqldb import PysqlDb
from pysqlcolor import *
from pysqlqueries import gatherCompleteSql
from pysqloraobjects import OraObject
import pysqlhelpers



def completeColumns(db, line, text, refList):
    """Find columns list to complete on
    @param line: line of sql text
    @param text: word we are currently completing
    @param refList: list of known tables/views/synonym of the current schema
    @return: list of columns (unicode)"""
    # Try to find tables/views name
    tables = pysqlhelpers.getKnownTablesViews(line.upper(), refList)
    columns = []
    for table in tables:
        oraObject = OraObject(objectName=table)
        oraObject.guessInfos(db)
        if oraObject is None:
            continue
        if oraObject.getType() == "SYNONYM":
            oraObject = oraObject.getTarget(db)
        columns.extend([i[0] for i in oraObject.getTableColumns(db)])

    #TODO: filter on proper table
    return [c for c in columns if c.startswith(text.upper())]


class CompleteGatheringWorker(Thread):
    """Background thread that will collect all completion terms
    from conf and dictionary"""

    def __init__(self, connect_string, completeLists):
        """
        @param connect_string: Oracle connection string to database
        @type connect_string: str
        @param completeLists: pointer to completions lists
        @type completeLists: dict. keys are themed, values list of words or dict"""
        self.connect_string = connect_string
        self.completeLists = completeLists
        Thread.__init__(self)
        self.setDaemon(True)


    def run(self):
        """Method executed when the thread object start() method is called"""
        time.sleep(0.5) # Small delay to let primary connection goes first
        self.db = PysqlDb(self.connect_string)
        self.gatherSID()
        time.sleep(0.5) # Another small delay to let primary connection goes first
        self.gatherSimpleObjects()

    def gatherSID(self):
        try:
            tnsnames = file(os.path.expandvars("$ORACLE_HOME/network/admin/tnsnames.ora")).readlines()
            self.completeLists["SID"] = sum([re.findall("^(\w+)\s*=", line) for line in tnsnames], [])
        except Exception, e:
            # Do not raise a PysqlException (useless)
            print RED + BOLD + _("Cannot open tnsnames.ora file (%s)") % e + RESET

    def gatherSimpleObjects(self):
        for objectType in ("table", "view", "index", "synonym", "sequence",
                           "directory", "trigger", "user"):
            objects = self.db.executeAll(gatherCompleteSql[objectType])
            self.completeLists[objectType] = [i[0] for i in objects]
