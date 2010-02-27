#!/usr/bin/python
# -*- coding: utf-8 -*-

""" This module defines all high level audit functions of pysql
@author: Sébastien Delcros (Sebastien.Delcros@gmail.com)
@license: GNU GPL V3
"""

# pylint: disable-msg=E1101

# Python imports:
import os

# Pysql imports:
from pysqlqueries import *
from pysqlexception import PysqlException, PysqlNotImplemented, PysqlActionDenied
from pysqloraobjects import *
from pysqlcolor import *
from pysqlconf import PysqlConf
from pysqldb import PysqlDb

# High level pysql audit functions
def listSnapshotId(db, numDays=1):
    """Prompts user to choose a snapshot id
    @arg db: connection object
    @arg numDays: the number of days of snapshots"""
    return db.executeAll(perfSql["snapshots"], [unicode(numDays)])

def addmReport(db, begin_snap="0", end_snap="0"):
    """Generates ADDM report
    @arg db: connection object
    @arg begin_snap: snapshot
    @arg end_snap: snapshot"""

    # Gets database id and instance number
    dbid = db.executeAll(perfSql["db_id"])[0][0]
    inum = db.executeAll(perfSql["instance_num"])[0][0]

    if begin_snap == "0" or end_snap == "0":
        raise PysqlException(_("Invalid snapshot pair: (%s ; %s)") % (begin_snap, end_snap))

    # PL/SQL procedure because of bloody in/out parameters in create_task function
    sql = """BEGIN
  DECLARE
    dbid  number;
    inum  number;
    bid   number;
    eid   number;
    id    number;
    name  varchar2(100);
    descr varchar2(500);

  BEGIN
    dbid := %s;
    inum := %s;
    bid  := %s;
    eid  := %s;
    name := '';
    descr := 'ADDM run: snapshots [' || bid || ', ' || eid || '], instance ' || inum || ', database id ' || dbid;

    -- create task
    dbms_advisor.create_task('ADDM', id, name, descr, null);

    -- set task parameters
    dbms_advisor.set_task_parameter(name, 'DB_ID', dbid);
    dbms_advisor.set_task_parameter(name, 'INSTANCE', inum);
    dbms_advisor.set_task_parameter(name, 'END_SNAPSHOT', eid);
    dbms_advisor.set_task_parameter(name, 'START_SNAPSHOT', bid);

    -- execute task
    dbms_advisor.execute_task(name);

    -- display task name
    dbms_output.enable;
    dbms_output.put_line(name);

  END;
END;
""" % (dbid, inum, begin_snap, end_snap)

    # Creates task
    try:
        db.execute(sql)
    except Exception, e:
        raise(_("Insufficient privileges"))
    # Gets task name
    task_name = db.getServerOuput()[0]
    # Generates report from task
    result = db.executeAll(perfSql["addm_report_text"], [task_name])
    return result

def awrReport(db, type="txt", begin_snap="0", end_snap="0"):
    """Generates AWR report
    @arg db: connection object
    @arg type: output format (html or text)
    @arg begin_snap: snapshot
    @arg end_snap: snapshot"""

    # Gets database id and instance number
    dbid = db.executeAll(perfSql["db_id"])[0][0]
    inum = db.executeAll(perfSql["instance_num"])[0][0]

    if begin_snap == "0" or end_snap == "0":
        raise PysqlException(_("Invalid snapshot pair: (%s ; %s)") % (begin_snap, end_snap))

    # Generates report
    try:
        if type.lower() == "html":
            result = db.executeAll(perfSql["awr_report_html"], [dbid, inum, begin_snap, end_snap])
        else:
            result = db.executeAll(perfSql["awr_report_text"], [dbid, inum, begin_snap, end_snap])
    except Exception, e:
        raise PysqlException(_("Insufficient privileges"))
    return result

def duReport(db, segmentType, tbs="%", user="%", nbRows=-1):
    """Generates storage report
    @arg db: connection object
    @arg segmentType: type (table or index)
    @arg tbs: tablespace to analyze, all if not specified
    @arg user: user to analyze, all users if not specified
    @arg nbRows: number of lines to return, all if not specified
    """
    # Gets storage size used considering user and tablespace restrictions
    size = db.executeAll(durptSql["nbTotalBlocks"], [tbs, user])[0][0]

    try:
    # Generates report
        if segmentType.lower() == "table":
            result = db.executeAll(durptSql["tablesForTbsAndUser"],  [unicode(size), tbs, user])
        elif segmentType.lower() == "index":
            result = db.executeAll(durptSql["indexesForTbsAndUser"], [unicode(size), tbs, user])
        else:
            raise(_("Internal error: type %s not supported") % segmentType)
    except Exception, e:
        raise PysqlException(_("Insufficient privileges"))

    return result[:nbRows]
