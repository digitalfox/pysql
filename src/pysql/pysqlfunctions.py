#!/usr/bin/python
# -*- coding: utf-8 -*-

""" This module defines all high level functions of pysql
@author: Sébastien Renard (sebastien.renard@digitalfox.org)
@author: Sébastien Delcros (Sebastien.Delcros@gmail.com)
@license: GNU GPL V3
"""

# pylint: disable-msg=E1101

# Python imports:
import os, re
from os import getenv, unlink
from difflib import ndiff

try:
    from hashlib import md5
except ImportError:
    # before python 2.5 hashlib did not exist
    from md5 import md5

# Pysql imports:
from pysqlqueries import *
from pysqlexception import PysqlException, PysqlNotImplemented, PysqlActionDenied
from pysqloraobjects import *
from pysqlcolor import *
from pysqlconf import PysqlConf
from pysqldb import PysqlDb
from pysqlhelpers import colorDiff, convert, addWildCardIfNeeded, generateWhere

# High level pysql functions
def count(db, objectName):
    """Counts rows in a table
    @arg objectName: table/view/M.View name
    @arg db: connection object
    @return: number of rows (int)"""
    # Gets the object type and owner
    oraObject = OraObject(objectName=objectName)
    oraObject.guessInfos(db)
    # Tries to resolve synonym and describe the target
    if oraObject.getType() == "SYNONYM":
        oraObject = oraObject.getTarget(db)
        if oraObject.getType() == "SYNONYM":
            # cannot desc, too much synonym recursion
            raise PysqlException(_("Too much synonym recursion"))
    if oraObject.getType() not in ("TABLE", "VIEW", "MATERIALIZED VIEW"):
        raise PysqlException(_("Cannot count rows of such object : %s") % oraObject.getType())
    return oraObject.getRowCount(db)

def compare(schemaA, schemaB):
    """Compares two Oracle schema and return the difference"""
    # First, compare list of tables
    tables = {}         # Store list of schema tables (key is schema)
    dbList = {}         # Store list of connect object to schema (key is schema)
    inAnotInB = []      # List of tables found in schema A but no present in schema B
    inBnotInA = []      # List of tables found in schema B but no present in schema A
    inAandB = []        # List of tables found in both schema A and schema B
    diffForAandB = {}   # Store common tables diff (key is table name)

    for schema in (schemaA, schemaB):
        dbList[schema] = PysqlDb(schema)
        keyword = searchObjectSql["table"][1]
        whereClause = """%s like '%%'""" % keyword
        sql = searchObjectSql["table"][0] % (
                        whereClause, schema.split("/")[0].upper(), keyword)
        result = dbList[schema].executeAll(sql)
        tables[schema] = [i[1] for i in result]

    for item in list(ndiff(tables[schemaA], tables[schemaB])):
        if item[0] == " ":
            inAandB.append(item[2:])
        elif item[0] == "-":
            inAnotInB.append(item[2:])
            item = "=" + item[1:]
        elif item[0] == "+":
            inBnotInA.append(item[2:])
        elif item[0] == "?":
            pass # diff helper control caracter to detail previous line.
        else:
            raise PysqlException(_("unknown diff control caracter (%s)") % item[0])
    # Compare tables found in both schema A and schema B
    for tableName in inAandB:
        diffForAandB[tableName] = compareTables(schemaA, schemaB, tableName, tableName, dbList, data=False)
    return (inAnotInB, inBnotInA, diffForAandB)

def compareTables(schemaA, schemaB, tableNameA, tableNameB, dbList=None, data=False):
    """
    Compares structure or data of tableA from schemaA with tableB from schemaB
    This is a wrapper to either compareTableStructure or compareTableData.
    @arg schemaA: connection string to the schema A
    @arg schemaB: connection string to the schema B
    @arg tableNameA: name of the table in schema A
    @arg tableNameB: name of the table in schema B
    @dbList:     hash list of PysqlDb object (keys are A & B). If None, new connections are opened.
    @arg data: if true, compare data else, compare structure
    """
    if dbList:
        # Convert schema name to anonymous A & B to avoid problem when schema are equal
        dbList["A"] = dbList[schemaA]
        dbList["B"] = dbList[schemaB]
    else:
        dbList = {} # Create new hash to store list of connect object to schema (key is schema)
        dbList["A"] = PysqlDb(schemaA)
        dbList["B"] = PysqlDb(schemaB)

    if data:
        return compareTableData(schemaA, schemaB, tableNameA, tableNameB, dbList)
    else:
        return compareTableStructure(schemaA, schemaB, tableNameA, tableNameB, dbList)

def compareTableStructure(schemaA, schemaB, tableNameA, tableNameB, dbList):
    """
    Compares structure of tableA from schemaA with tableB from schemaB
    @arg schemaA: connection string to the schema A
    @arg schemaB: connection string to the schema B
    @tableNameA: name of the table in schema A
    @tableNameB: name of the table in schema B
    @dbList:     hash list of PysqlDb object (keys are A & B).
    """
    tableDesc = {}      # Store the current table desc for each schema (key is schema)
    for schema, tableName in (("A", tableNameA), ("B", tableNameB)):
        #BUG: format is ugly. use/merge with __displayTab algo ??
        tableDesc[schema] = ["     ".join([str(i) for i in line])
                            for line in desc(dbList[schema], tableName, None, False)[1]]
        if not tableDesc[schema]:
            raise PysqlException(_("Could not find table %s") % tableName)

    if tableDesc["A"] == tableDesc["B"]:
        result = None
    else:
        result = colorDiff(ndiff(tableDesc["A"], tableDesc["B"]))
    return result

def compareTableData(schemaA, schemaB, tableNameA, tableNameB, dbList):
    """
    Compares data of tableA from schemaA with tableB from schemaB
    @arg schemaA: connection string to the schema A
    @arg schemaB: connection string to the schema B
    @tableNameA: name of the table in schema A
    @tableNameB: name of the table in schema B
    @dbList:     hash list of PysqlDb object (keys are A & B).
    """
    # Check that table structure (columns names & type) are similar
    tableStruct = {}  # Store table structure (columns names & tupe) for each schema (key is schema)
    tablePK = {}      # Store table primary key list for each schema (key is schema)
    tableNCol = {}    # Store table number of column for each schema (key is schema)
    for schema, tableName in (("A", tableNameA), ("B", tableNameB)):
        table = OraObject(dbList[schema].getUsername(), tableName)
        table.guessInfos(dbList[schema])
        if table.getType() == "TABLE":
            # Get PK and number of columns
            tablePK[schema] = table.getPrimaryKeys(dbList[schema])
            tableNCol[schema] = table.getNumberOfColumns(dbList[schema])
            # Get only column name (0) and column type (1)
            tableStruct[schema] = [[i[0], i[1]] for i in table.getTableColumns(dbList[schema])]
        else:
            raise PysqlException(_("%s does not seem to be a table in %s") %
                                   (tableName, dbList[schema].getConnectString()))

    if tableStruct["A"] != tableStruct["B"]:
        raise PysqlException(
         _("Unable to compare data of tables that do not have same structure (columns name and type)"))

    if tablePK["A"] == tablePK["B"] and tablePK["A"]: # identical and not None
        order = "order by %s" % (", ".join(tablePK["A"]))
    else:
        order = "order by %s" % ", ".join(str(i + 1) for i in range(tableNCol["A"]))
    for schema, tableName in (("A", tableNameA), ("B", tableNameB)):
        # test cursor size. Should make a quick bench to choose the good one
        dbList[schema].execute("select * from %s %s" % (tableName, order), fetch=False, cursorSize=10000)
    result = {}     # Store current fecth. Key is A or B
    moreRows = {}   # Flag to indicate there's more rows in cursor. Key is A or B
    moreRows["A"] = True
    moreRows["B"] = True
    diff = []       # Store diff lines in this list
    while moreRows["A"] and moreRows["B"]:
        for schema in ("A", "B"):
            result[schema], moreRows[schema] = dbList[schema].fetchNext()
            if result[schema]:
                #TODO: performance of this part is very very bad
                result[schema] = ["     ".join([str(i) for i in line])
                            for line in result[schema]]
        for line in colorDiff(ndiff(result["A"], result["B"])):
            if line[0] != " ":
                if diff and line[2:] == diff[-1][2:]:
                    diff.pop() # simple double removing for one line decay only
                else:
                    diff.append(line)
    for sign, schema in (("-", "A"), ("+", "B")):
        while moreRows[schema]:
            result[schema], moreRows[schema] = dbList[schema].fetchNext()
            result[schema] = ["     ".join([str(i) for i in line])
                            for line in result[schema]] # This code should be factorised with above
            diff.append("%s %s" % (sign, result[schema]))
    # Make a second pass to remove doublon accross two resultset
    #BUG: does not work in all case
    oldSign = ""
    newSign = ""
    oldBuffer = []
    newBuffer = []
    newBlock = True # Flag to indicate we have to start a new matching block
    i = 0
    diff.append(" ") # Add a mark to allow final lines processing
    toBeRemoved = []   # List of item index to be removed
    for line in diff:
        newSign = line[0]
        if oldSign == newSign or newBlock:
            # Append to new Buffer
            newBuffer.append(line[2:])
            newBlock = False
        else:
            if newBuffer == oldBuffer:
                # Detect doublons
                for j in range(len(newBuffer) * 2):
                    toBeRemoved.append(i - j - 1)
                newBlock = True
            # Changing to next block
            oldBuffer = newBuffer
            newBuffer = [line[2:]]
        oldSign = newSign
        i += 1
    diff = [diff[i] for i in xrange(len(diff) - 1) if i not in toBeRemoved]
    return diff

def ddl(db, objectName):
    """Gets the ddl of an object
    @return: ddl as string"""
    oraObject = OraObject(objectName=objectName)
    oraObject.guessInfos(db)
    if oraObject.getType() == "":
        return None
    else:
        return oraObject.getDDL(db)

def desc(db, objectName, printDetails=True, printStats=False, sort=False):
    """Describes an object
    @param objectName: object to be described
    @return: header and resultset of definition as a tuple (header, definition)
    ==> This function should be split in two parts: one in pysqlOraObjects for object self description
    the other one here as a describe function that encapsulate pysqlOraObjects manipulation"""

    header = []
    result = []

    # Reads conf
    conf = PysqlConf.getConfig()
    unit = conf.get("unit") # Unit used to format data

    # Look for object type if given
    matchResult = re.match("(.*) \((.+)\)", objectName)
    if matchResult:
        oraObject = OraObject(objectName=matchResult.group(1),
                              objectType=matchResult.group(2))
    else:
        oraObject = OraObject(objectName=objectName)

    # Gets the object type and owner
    oraObjectSet = oraObject.guessInfos(db, interactive=True)


    if len(oraObjectSet) == 1:
        oraObject = oraObjectSet.pop()
    elif len(oraObjectSet) > 1:
        print CYAN + _("Got multiple result:") + "\n-" + RESET,
        print "\n- ".join([str(x) for x in oraObjectSet])
        # Looking for own object
        ownOraObjects = [o for o in oraObjectSet if o.getOwner() == db.getUsername().upper()]
        publicOraObjects = [o for o in oraObjectSet if o.getOwner() == "PUBLIC"]
        if len(ownOraObjects) == 1:
            oraObject = ownOraObjects.pop()
            print BOLD + RED + _("Defaulting to own object: %s") % oraObject + RESET
        # Looking for public objects
        elif len(publicOraObjects) == 1:
            oraObject = publicOraObjects.pop()
            print BOLD + RED + _("Defaulting to public object: %s") % oraObject + RESET
    else:
        # No result
        return ([], [])

    # Object or type unknown?
    if oraObject.getType() == "":
        return ([], [])

    # Tries to resolve synonym and describe the target
    if oraObject.getType() == "SYNONYM":
        oraObject = oraObject.getTarget(db)
        if oraObject.getType() == "SYNONYM":
            # cannot desc, too much synonym recursion
            return ([], [])

    # Guess object status
    oraObject.guessStatus(db)

    # Displays some information about the object
    if printDetails:
        print CYAN + _("Name") + "\t: " + oraObject.getName() + RESET
        print CYAN + _("Type") + "\t: " + oraObject.getType() + RESET
        print CYAN + _("Owner") + "\t: " + oraObject.getOwner() + RESET
        if oraObject.getStatus() in ("INVALID", "OFFLINE", "UNUSED"):
            print CYAN + _("Status") + "\t\t: " + BOLD + RED + oraObject.getStatus() + RESET
        else:
            print CYAN + _("Status") + "\t\t: " + oraObject.getStatus() + RESET
        if oraObject.getType() in ("TABLE", "TABLE PARTITION", "INDEX", "INDEX PARTITION"):
            try:
                print CYAN + _("Tablespace") + "\t: " + oraObject.getTablespace(db).getName() + RESET
            except PysqlException:
                print CYAN + _("Tablespace") + "\t: " + _("<unable to get tablepsace name>") + RESET
            try:
                print CYAN + _("Partitioned?") + "\t: " + (oraObject.isPartitioned(db) and _("Yes") or _("No")) + RESET
            except PysqlException:
                print CYAN + _("Partitioned?") + "\t: " + _("<unable to get partition information>") + RESET
        if oraObject.getType() in ("TABLE", "TABLE PARTITION", "VIEW", "MATERIALIZED VIEW"):
            try:
                print CYAN + _("Comment") + "\t: " + oraObject.getComment(db) + RESET
            except PysqlException:
                print CYAN + _("Comment") + "\t: " + _("<unable to get comment>") + RESET
        if oraObject.getType() not in ("DATA FILE", "TABLESPACE", "USER"):
            try:
                print CYAN + _("Created on") + "\t: " + oraObject.getCreated(db) + RESET
            except PysqlException:
                print CYAN + _("Created on") + "\t: " + _("<unable to get date of creation>") + RESET
            try:
                print CYAN + _("Last DDL on") + "\t: " + oraObject.getLastDDL(db) + RESET
            except PysqlException:
                print CYAN + _("Last DDL on") + "\t: " + _("<unable to get date of last DDL modification>") + RESET

    # Displays some statistics about the object
    if printStats:
        if oraObject.getType() in ("TABLE", "TABLE PARTITION"):
            try:
                print ORANGE + _("Last analyzed on") + ": " + str(oraObject.getLastAnalyzed(db)) + RESET
            except PysqlException:
                print CYAN + _("Last analyzed on") + "\t: " + _("<unable to get date of last statistics computation>") + RESET
            try:
                print ORANGE + _("Nb rows") + "\t\t: " + str(oraObject.getNumRows(db)) + RESET
            except PysqlException:
                print CYAN + _("Nb rows") + "\t: " + _("<unable to get number of rows>") + RESET
            try:
                print ORANGE + _("Nb used blocks") + "\t: " + str(oraObject.getUsedBlocks(db)) + RESET
            except PysqlException:
                print ORANGE + _("Nb used blocks") + "\t: " + _("<unable to get number of used blocks>") + RESET
            try:
                print ORANGE + _("Avg row length") + "\t: " + str(oraObject.getAvgRowLength(db)) + RESET
            except PysqlException:
                print CYAN + _("Avg row length") + "\t: " + _("<unable to get average row length") + RESET

    # Evaluates object type (among the 24 defined)
    if oraObject.getType() in ("TABLE" , "TABLE PARTITION"):
        header = [_("Name"), _("Type"), _("Null?"), _("Comments"), _("Indexes")]
        columns = oraObject.getTableColumns(db, sort)

        # Gets indexed columns of the table
        indexedColumns = oraObject.getIndexedColumns(db)
        # Format index this way: index_name(index_position)
        #TODO: handle database encoding instead of using just str()
        indexedColumns = [[i[0], i[1] + "(" + str(i[2]) + ")"] for i in indexedColumns]
        for column in columns:
            column = list(column) # change tuple to list
            indexInfo = [i[1] for i in indexedColumns if i[0] == column[0]]
            column.append(", ".join(indexInfo))
            result.append(column)

    elif oraObject.getType() in ("VIEW", "MATERIALIZED VIEW"):
        header = [_("Name"), _("Type"), _("Null?"), _("Comments")]
        result = oraObject.getTableColumns(db)

    elif oraObject.getType() == "CONSUMER GROUP":
        raise PysqlNotImplemented()

    elif oraObject.getType() == "CONTEXT":
        raise PysqlNotImplemented()

    elif oraObject.getType() == "DATA FILE":
        header = [_("Tablespace"), _("Size (%s)") % unit.upper(), _("Free (%s)") % unit.upper(), _("%Used")]
        size = convert(oraObject.getAllocatedBytes(db), unit)
        free = convert(oraObject.getFreeBytes(db), unit)
        if size != 0:
            used = 100 - float(100 * free) / size
        else:
            used = 0
        if printDetails:
            print CYAN + _("Tablespace: ") + oraObject.getTablespace(db).getName() + RESET
        result = [[oraObject.getTablespace(db).getName(), round(size, 2), round(free, 2), round(used, 2)]]

    elif oraObject.getType() == "DATABASE LINK":
        header = [_("Target")]
        result = [[oraObject.getRemoteUser(db) + "@" + oraObject.getRemoteHost(db)]]

    elif oraObject.getType() == "DIRECTORY":
        header = [_("Path")]
        result = [[oraObject.getPath(db)]]

    elif oraObject.getType() == "EVALUATION CONTEXT":
        raise PysqlNotImplemented()

    elif oraObject.getType()in("FUNCTION", "PACKAGE", "PROCEDURE"):
        header = [_("#"), _("Source")]
        result = oraObject.getSource(db)

    elif oraObject.getType() == "INDEX":
        header = [_("Property"), _("Value")]
        result = oraObject.getProperties(db)

    elif oraObject.getType() == "INDEX PARTITION":
        raise PysqlNotImplemented()

    elif oraObject.getType() == "INDEXTYPE":
        raise PysqlNotImplemented()

    elif oraObject.getType() == "JAVA CLASS":
        raise PysqlNotImplemented()

    elif oraObject.getType() == "JAVA DATA":
        raise PysqlNotImplemented()

    elif oraObject.getType() == "JAVA RESOURCE":
        raise PysqlNotImplemented()

    elif oraObject.getType() == "LIBRARY":
        raise PysqlNotImplemented()

    elif oraObject.getType() == "OPERATOR":
        raise PysqlNotImplemented()

    elif oraObject.getType() == "PACKAGE BODY":
        raise PysqlNotImplemented()

    elif oraObject.getType() == "SEQUENCE":
        header = [_("Last"), _("Min"), _("Max"), _("Step")]
        result = [[oraObject.getLast(db), oraObject.getMin(db), oraObject.getMax(db), oraObject.getStep(db)]]

    elif oraObject.getType() == "TABLE PARTITION":
        raise PysqlNotImplemented()

    elif oraObject.getType() == "TABLESPACE":
        oraObject.updateDatafileList(db)
        header = [_("Datafile"), _("Size (%s)") % unit.upper(), _("Free (%s)") % unit.upper(), _("%Used")]
        result = [[]]
        totalSize = 0
        totalFree = 0
        totalUsed = 0
        for datafile in oraObject.getDatafiles():
            name = datafile.getName()
            size = convert(datafile.getAllocatedBytes(db), unit)
            free = convert(datafile.getFreeBytes(db), unit)
            if size != 0:
                used = 100 - float(100 * free) / size
            else:
                used = 0
            result.append([name, round(size, 2), round(free, 2), round(used, 2)])
            totalSize += size
            totalFree += free
        if totalSize != 0:
            totalUsed = 100 - float(100 * totalFree) / totalSize
        else:
            totalUsed = 0
        if len(oraObject.getDatafiles()) > 1:
            result[0] = ["> " + _("TOTAL"), round(totalSize, 2), round(totalFree, 2), round(totalUsed, 2)]
        else:
            result.pop(0)

    elif oraObject.getType() == "TRIGGER":
        oraObject.updateTable(db)
        header = [_("Status"), _("Table"), _("Type"), _("Event"), _("Body")]
        result = [[oraObject.getStatus(db), oraObject.getTable(db).getFullName(),
                 oraObject.getTriggerType(db), oraObject.getEvent(db),
                 oraObject.getBody(db).replace("\n", " ")]]

    elif oraObject.getType() == "USER":
        oraObject.updateTablespaceList(db)
        header = [_("Tablespace"), _("Default?"), _("#Tables"), _("#Indexes")]
        result = [[]]
        totalTables = 0
        totalIndexes = 0
        defaultTbs = oraObject.getDefaultTablespace(db)
        #tempTbs = oraObject.getTempTablespace(db)
        for tablespace in oraObject.getTablespaces():
            name = tablespace.getName()
            nbTables = oraObject.getNbTables(db, tablespace=tablespace.getName())
            nbIndexes = oraObject.getNbIndexes(db, tablespace=tablespace.getName())
            if name == defaultTbs:
                defstr = u"*"
            else:
                defstr = u""
            result.append([name, defstr, nbTables, nbIndexes])
            totalTables += nbTables
            totalIndexes += nbIndexes
        if len(oraObject.getTablespaces()) > 1:
            result[0] = ["> " + _("TOTAL"), u"", totalTables, totalIndexes]
        else:
            result.pop(0)
    else:
        raise PysqlException(_("Type not handled: %s") % oraObject.getType())
    return (header, result)

def edit(db, objectName, content=""):
    """Edits properties of an Oracle object
    @param objectName: name of the object to edit
    @return: True if object has been found correctly updated. Else, return False
    """
    # Gets the object type and owner
    oraObject = OraObject(objectName=objectName)
    oraObject.guessInfos(db)

    # Object or type unknown?
    if oraObject.getType() is None:
        return False

    # Tries to resolve synonym and describe the target
    if oraObject.getType() == "SYNONYM":
        oraObject = oraObject.getTarget(db)
        if oraObject.getType() == "SYNONYM":
            raise PysqlException(_("Too much synonym recursion"))
    if content == "":
        try:
            content = oraObject.getSQL(db)
        except AttributeError:
            raise PysqlNotImplemented()
    content = editor(content)
    # Does nothing if data does not change
    if content is None:
        return True
    # Validates it (for view it is SQL code)
    db.validate(content)
    # And update it in database
    try:
        oraObject.setSQL(db, content)
    except AttributeError:
        # SetSQL failed because it is not (yet) implemented
        raise PysqlNotImplemented()
    return True

def editor(content=""):
    """Edits content with systemp editor
    @arg content: initial data to edit. Default is empty string
    @type content: string
    @return: None is content does not change, else modified content
    """
    # Which editor, which temporary directory?
    if os.name == "posix":
        editorProgram = getenv("EDITOR", "vi")
        tempDir = "/tmp"
    elif os.name == "nt":
        editorProgram = "edit"
        tempDir = getenv("TEMP", ".")
    else:
        raise PysqlException(_("No editors are supported on this platform. Sorry."))
    # Computes actual properties md5
    checkSum = md5(content).hexdigest()
    try:
        # Writes actual properties to temp file
        filePath = os.path.join(tempDir, "pysql-" + str(os.getpid()) + ".tmp")
        tmp = file(filePath, "w")
        tmp.write(content)
        tmp.close()
        # Lets the user edit it
        exitStatus = os.system(editorProgram + " " + filePath)
        if exitStatus != 0:
            raise PysqlException(_("Editor exited with status %s") % exitStatus)
        # Updates properties with new value
        tmp = file(filePath, "r")
        content = tmp.read()
        tmp.close()
        unlink(filePath)
    except IOError, e:
        raise PysqlException(_("Error while using temporary file (%s)") % e)
    if checkSum == md5(content).hexdigest():
        return None
    else:
        return content

def explain(db, statement):
    """Computes and displays explain plan for statement
    @param statement: sql statement to be explained
    @return: explain plan (list of string)
    """
    # Compute the explain plan
    db.execute("explain plan for %s" % statement)
    return db.executeAll(u"""select plan_table_output
                from table(dbms_xplan.display('PLAN_TABLE',null,'serial'))""")

def objectsLock(db):
    """Displays locks on objects
    @return: resultset in tabular format
    """
    header = [_("User"), _("Program"), _("OS user"), _("Mode"), _("Object")]
    try:
        result = db.executeAll(lockSql["objects"])
    except PysqlException:
        raise PysqlActionDenied(_("Insufficient privileges"))
    return (header, result)

def sessionsLock(db):
    """Displays sessions lock that block other sessions
    @return: resultset in tabular format
    """
    header = [_("Blocking session"), _("Blocked session")]
    try:
        result = db.executeAll(lockSql["sessions"])
    except PysqlException:
        raise PysqlActionDenied(_("Insufficient privileges"))
    return (header, result)



def sessions(db, all=False, search=None):
    """Returns top session, filter by "sort"
    @param all: Show all sessions, not only active (top) session
    @type all: bool
    @param search: search session program, name, ouser... that looks like the str given
    @return: huge resultset in tabular format"""

    header = [_("Id"), _("Serial"), _("Schema"), _("OsUser"), _("Machine"), _("Program"), _("Logged Since"), _("Blk Gets"), _("Cons Gets"), _("Phy Rds"), _("Blk Chg"), _("Cons Chg"), _("CPU(ms)"), _("C PID"), _("S PID"), _("SQL")]

    sessionFilter = []
    if not all:
        sessionFilter.append("a.Status != 'INACTIVE'")
    if search:
        for searchTerm in search:
            searchFilter = []
            for term in ("a.SchemaName", "a.Osuser", "a.Machine", "a.Program", "d.sql_text"):
                searchFilter.append("%s like '%%%s%%'" % (term, searchTerm))
            sessionFilter.append("(%s)" % " or ".join(searchFilter))

    if sessionFilter:
        whereClause = "and %s" % " and ".join(sessionFilter)
    else:
        whereClause = ""
    try:
        result = db.executeAll(sessionStatSql["all"] % whereClause)
    except PysqlException:
        raise PysqlActionDenied(_("Insufficient privileges"))
    return (header, result)

def sessionStat(db, sid, stat=None):
    """Displays detailed statistics for one session
    @param stat: can be ios, locks, waitEvents, openCurors, details
    @return: array of results"""
    # TODO: harden this weak code!
    if stat is None:
        return None
    else:
        return db.executeAll(sessionStatSql[stat], [sid])

def killSession(db, session, immediate=False):
    """Kills the given sessions
    @param session: 'session-id,session-serial'
    @type session: str
    @param immediate: sends the immediate option to kill
    @type immediate: bool
    @return: None but raises an exception if session does not exist
    """
    sql = u"""alter system kill session '%s'""" % session
    if immediate:
        sql += u" immediate"
    try:
        db.execute(sql)
    except PysqlException:
        raise PysqlActionDenied(_("Insufficient privileges"))

def showParameter(db, param=""):
    """Shows the session parameters matching the pattern 'param'
    @param param: pattern to be matched
    @type param: str
    @return: resultset in tabular format
    """
    param = addWildCardIfNeeded(param)
    header = [_("Name"), _("Type"), _("Value"), _("#"), _("Session?"), _("System?"), _("Comments")]
    #TODO: move this request to pysqlQueries
    try:
        result = db.executeAll("""select name
            , decode(type, 1, 'BOOLEAN', 2, 'STRING', 3, 'INTEGER', 4, 'PFILE'
                         , 5, 'RESERVED', 6, 'BIG INTEGER', 'UNKNOWN') type
            , decode(substr(name, 1, 3), 'nls'
                            ,  (select value from nls_session_parameters
                                where lower(parameter)=name)
                            , value) value
            , ordinal
            , isses_modifiable
            , issys_modifiable
            , description
        from v$parameter2
        where name like '%s'
        order by 1""" % param)
    except PysqlException:
        raise PysqlActionDenied(_("Insufficient privileges"))
    return (header, result)

def showServerParameter(db, param=""):
    """Shows the server parameters matching the pattern 'param'
    @param param: pattern to be matched
    @type param: str
    @return: resultset in tabular format
    """
    param = addWildCardIfNeeded(param)
    header = [_("Name"), _("Type"), _("Value"), _("#"), _("Used?"), _("Comments")]
    #TODO: move this request to pysqlQueries
    try:
        result = db.executeAll("""select distinct sp.name
            , decode(p.type, 1, 'BOOLEAN', 2, 'STRING', 3, 'INTEGER', 4, 'PFILE'
                           , 5, 'RESERVED', 6, 'BIG INTEGER', 'UNKNOWN') type
            , decode(substr(sp.name, 1, 3), 'nls'
                            ,  (select value from nls_database_parameters
                                where lower(parameter)=sp.name)
                            , sp.value) value
            , sp.ordinal
            , sp.isspecified
            , p.description
        from v$spparameter sp, v$parameter2 p
        where sp.name=p.name
          and sp.name like '%s'
        order by 1""" % param)
    except PysqlException:
        raise PysqlActionDenied(_("Insufficient privileges"))
    return (header, result)

# Oracle object searching
def searchObject(db, objectType, objectName, objectOwner):
    """Searches for Oracle objects by name with wildcard if needed"""
    result = {}
    objectType = objectType.lower()
    try:
        sql = searchObjectSql[objectType][0]
        keyword = searchObjectSql[objectType][1]
        if len(objectName.split()) == 1:
            # Single word search. Just add wildcart % if needed
            whereClause = "%s like '%s'" % (keyword, addWildCardIfNeeded(objectName))
        else:
            whereClause = generateWhere(keyword, objectName)
        objects = db.executeAll(sql % (whereClause, objectOwner, keyword))
    except KeyError:
        raise PysqlException(_("SQL entry not defined for searchObjectSql: %s") % objectType)
    # Returns a dict with key=schemaNAme and Value=list of object
    for (owner, name) in objects:
        if result.has_key(owner):
            result[owner].append(name)
        else:
            result[owner] = [name]
    return result
