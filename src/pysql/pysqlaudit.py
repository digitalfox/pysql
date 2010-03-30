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
    try:
        return db.executeAll(perfSql["snapshots"], [unicode(numDays)])
    except Exception, e:
        raise PysqlActionDenied(_("Insufficient privileges"))

def addmReport(db, begin_snap="0", end_snap="0", type="TEXT", level="TYPICAL"):
    """Generates ADDM report
    @arg db: connection object
    @arg begin_snap: snapshot
    @arg end_snap: snapshot"""

    # Gets database id and instance number
    try:
        dbid = db.executeAll(perfSql["db_id"])[0][0]
        inum = db.executeAll(perfSql["instance_num"])[0][0]
    except Exception, e:
        raise PysqlActionDenied(_("Insufficient privileges"))

    if begin_snap == "0" or end_snap == "0":
        raise PysqlActionDenied(_("Invalid snapshot pair: (%s ; %s)") % (begin_snap, end_snap))

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

    -- creates task
    dbms_advisor.create_task('ADDM', id, name, descr, null);

    -- sets task parameters
    dbms_advisor.set_task_parameter(name, 'DB_ID', dbid);
    dbms_advisor.set_task_parameter(name, 'INSTANCE', inum);
    dbms_advisor.set_task_parameter(name, 'END_SNAPSHOT', eid);
    dbms_advisor.set_task_parameter(name, 'START_SNAPSHOT', bid);

    -- executes task
    dbms_advisor.execute_task(name);

    -- displays task name
    dbms_output.enable;
    dbms_output.put_line(name);

  END;
END;
""" % (dbid, inum, begin_snap, end_snap)

    # Creates task
    try:
        db.execute(sql)
    except Exception, e:
        raise PysqlException(_("Insufficient privileges"))
    # Gets task name
    task_name = db.getServerOuput()[0]
    # Generates report from task
    result = db.executeAll(perfSql["addm_report_text"], [unicode(task_name), unicode(type.upper()), unicode(level.upper())])
    return result

def awrReport(db, type="txt", begin_snap="0", end_snap="0"):
    """Generates AWR report
    @arg db: connection object
    @arg type: output format (html or text)
    @arg begin_snap: snapshot
    @arg end_snap: snapshot"""

    # Gets database id and instance number
    try:
        dbid = db.executeAll(perfSql["db_id"])[0][0]
        inum = db.executeAll(perfSql["instance_num"])[0][0]
    except Exception, e:
        raise PysqlActionDenied(_("Insufficient privileges"))

    if begin_snap == "0" or end_snap == "0":
        raise PysqlActionDenied(_("Invalid snapshot pair: (%s ; %s)") % (begin_snap, end_snap))

    # Generates report
    try:
        if type.upper() == "HTML":
            result = db.executeAll(perfSql["awr_report_html"], [dbid, inum, begin_snap, end_snap])
        else:
            result = db.executeAll(perfSql["awr_report_text"], [dbid, inum, begin_snap, end_snap])
    except Exception, e:
        raise PysqlActionDenied(_("Insufficient privileges"))
    return result

def sqlTune(db, statement, type="TEXT", level="TYPICAL"):
    """Generates a SQL tunung advice report
    @arg db: connection object
    @arg statement: sql statement to be tuned
    """
    # Doubles quote because of sql statement parsing
    statement = statement.replace("'", "''")

    # PL/SQL procedure because of bloody in/out parameters in create_task function
    sql = """BEGIN
  DECLARE
    sql_text  clob;
    user_name varchar2(30);
    task_name varchar2(30);

  BEGIN
    sql_text  := '%s';
    user_name := '%s';
    task_name := '';

    -- creates new task
    task_name := dbms_sqltune.create_tuning_task(
        sql_text    => sql_text,
        scope       => 'comprehensive',
        time_limit  => 60,
        task_name   => task_name,
        description => 'task to tune a query');

    -- executes task
    dbms_sqltune.execute_tuning_task(task_name => task_name);

    -- displays task name
    dbms_output.enable;
    dbms_output.put_line(task_name);
  END;
END;
""" % (statement, db.getUsername())

    # Creates task
    try:
        db.execute(sql)
    except PysqlException, e:
        raise PysqlException(_("Insufficient privileges"))
    # Gets task name
    task_name = db.getServerOuput()[0]
    # Generates report from task
    try:
        result = db.executeAll(perfSql["sqltune_text"], [unicode(task_name), unicode(type.upper()), unicode(level.upper())])
    except PysqlException, e:
        if str(e).count(unicode(task_name)) > 0:
            raise PysqlException(_("Insufficient privileges"))
        else:
            raise e

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
    try:
        size = db.executeAll(durptSql["nbTotalBlocks"], [tbs, user])[0][0]
    except PysqlException, e:
        raise PysqlActionDenied(_("Insufficient privileges"))

    # Generates report
    if segmentType.lower() == "table":
        header = [_("Owner"), _("Tablespace"), _("Table"), _("Part?"), _("#Cols"), _("#Rows"), _("Size(blk)"), _("Size(MB)"), _("Size(%)")]
        result = db.executeAll(durptSql["tablesForTbsAndUser"],  [unicode(size), tbs, user])
    elif segmentType.lower() == "index":
        header = [_("Owner"), _("Tablespace"), _("Index"), _("Part?"), _("Level"), _("Keys"), _("Size(blk)"), _("Size(MB)"), _("Size(%)")]
        result = db.executeAll(durptSql["indexesForTbsAndUser"], [unicode(size), tbs, user])
    else:
        raise PysqlException(_("Internal error: type %s not supported") % segmentType)

    return (result[:nbRows], header)

def assmReport(db, name):
    """Generates a storage report (may take a while)
    @arg db: connection object
    @arg name: table name
    """
    table = OraTable(tableName=name)
    table.guessInfos(db)
    try:
        neededBlocks = table.getNeededBlocks(db)
    except PysqlException, e:
        raise PysqlException(_("Table %s does not exist") % table.getName())
    try:
        allocatedBlocks = table.getUsedBlocks(db)
    except PysqlException, e:
        raise PysqlActionDenied(_("Insufficient privileges"))
    lostBlocks = allocatedBlocks - neededBlocks

    header = [_("Owner"), _("Name"), _("Allocated"), _("Needed"), _("Lost"), _("Lost(%)")]
    result = [[table.getOwner(), table.getName(), allocatedBlocks, neededBlocks, lostBlocks, round(100*float(lostBlocks)/allocatedBlocks, 1)]]

    return (result, header)

