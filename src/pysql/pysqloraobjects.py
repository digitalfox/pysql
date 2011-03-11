#!/usr/bin/python
# -*- coding: utf-8 -*-

"""This module defines some classes to make easier Oracle object manipulation
@author: Sébastien Renard (sebastien.renard@digitalfox.org)
@author: Sébastien Delcros (Sebastien.Delcros@gmail.com)
@license: GNU GPL V3
"""

# pylint: disable-msg=E1101

# Pysql imports:
from pysqlqueries import *
from pysqlexception import PysqlException, PysqlNotImplemented, PysqlActionDenied
import pysqlhelpers

class OraObject:
    """Father of all pysql Oracle objects"""
    def __init__(self, objectOwner="", objectName="", objectType="", objectStatus=""):
        """Object creation"""
        self.setOwner(objectOwner) # Set owner first because setName may override
        self.setName(objectName)
        self.setType(objectType)
        self.setStatus(objectStatus)

    def __str__(self):
        """String representation (mostly used for debug purpose)"""
        return self.getOwner() + "." + self.getName() + " (" + self.getType() + ")"

    def __eq__(self, other):
        """Define equal operator. Object are identical if they have same name, type and owner"""
        if hash(self) == hash(other):
            return True
        else:
            return False

    def __hash__(self):
        """Unique hash of object. Used to determine if objects are identical and to create
        set of unique object"""
        return hash("%s.%s.%s" % (self.getType(), self.getOwner(), self.getName()))

    def getCopy(self):
        """@return: a deep copy of the current object"""
        return OraObject(objectOwner=self.getOwner(), objectName=self.getName(), objectType=self.getType())

    def getName(self):
        """@return: object name (str)"""
        return self.objectName

    def getFullName(self):
        """@return: object name prefixed with owner name (str)
        Ex. "scott.my_table" """
        return self.getOwner() + "." + self.getName()

    def getType(self):
        """@return: object type (str)"""
        return self.objectType

    def getOwner(self):
        """@return: object owner (str)"""
        return self.objectOwner

    def getStatus(self):
        """@return: object status (str)"""
        return self.objectStatus

    def setName(self, objectName):
        """ Sets name (and owner if name is given like "user.object")"""
        if objectName == "":
            raise PysqlException("Object name must be defined!")
        if objectName.startswith("/"):
            # This should be a datafile
            #TODO: check if fully compliant with Windows
            self.objectName = objectName
        elif objectName.count(".") == 1:
            (owner, name) = objectName.split(".")
            self.setOwner(owner)
            self.objectName = pysqlhelpers.upperIfNoQuotes(name)
        else:
            # Default to simple setName
            self.objectName = pysqlhelpers.upperIfNoQuotes(objectName)

    def setType(self, objectType):
        """Sets the object type
        @param objectType: Oracle object type as defined in Oracle dynamic views
        @type objectType: str
        """
        if objectType is None:
            self.objectType = ""
        else:
            self.objectType = objectType.upper()
        # Transtypes to object type if possible
        if   self.objectType == "DATABASE LINK":
            self.__class__ = OraDBLink
        elif self.objectType == "DATA FILE":
            self.__class__ = OraDatafile
        elif self.objectType == "DIRECTORY":
            self.__class__ = OraDirectory
        elif self.objectType == "FUNCTION":
            self.__class__ = OraFunction
        elif self.objectType in ("INDEX", "INDEX PARTITION"):
            self.__class__ = OraIndex
        elif self.objectType == "MATERIALIZED VIEW":
            self.__class__ = OraMaterializedView
        elif self.objectType == "PACKAGE":
            self.__class__ = OraPackage
        elif self.objectType == "PACKAGE BODY":
            self.__class__ = OraPackageBody
        elif self.objectType == "PROCEDURE":
            self.__class__ = OraProcedure
        elif self.objectType == "SEQUENCE":
            self.__class__ = OraSequence
        elif self.objectType == "SYNONYM":
            self.__class__ = OraSynonym
        elif self.objectType in ("TABLE", "TABLE PARTITION"):
            self.__class__ = OraTable
        elif self.objectType == "TABLESPACE":
            self.__class__ = OraTablespace
        elif self.objectType == "TRIGGER":
            self.__class__ = OraTrigger
        elif self.objectType == "VIEW":
            self.__class__ = OraView
        elif self.objectType == "USER":
            self.__class__ = OraUser

    def setOwner(self, objectOwner):
        """Sets the object owner. Name is uppercased if quote are not given"""
        self.objectOwner = pysqlhelpers.upperIfNoQuotes(objectOwner)

    def setStatus(self, objectStatus):
        self.objectStatus = objectStatus

    def guessStatus(self, db):
        """guess the object status"""
        status = db.executeAll(guessInfoSql["objectStatusFromName"], [self.getName()])
        self.setStatus(status[0][0])

    def guessInfos(self, db, interactive=False):
        """Guesses and sets object type, owner and status
        @param db: Connection to Oracle
        @type db: PysqlDb instance
        @param interactive: should we prompt user if multiple results are found? (default is False)
        @type interactive: bool
        @return: True if type and owner are guessed. In interactive mode, returns list of objects found
        """
        #TODO: this code should be factorized
        result = set() # Store here all guessInfos results
        currentUsername = db.getUsername().upper()
        name = self.getName()
        owner = self.getOwner()

        # Assume object is in current schema
        if owner == "":
            objectType = db.executeAll(guessInfoSql["typeFromNameAndOwner"], [name, currentUsername])
            for type in objectType:
                if interactive:
                    result.add(OraObject(currentUsername, name, type[0]))
                else:
                    self.setOwner(currentUsername)
                    self.setName(name)
                    self.setType(type[0])
                    self.guessStatus(db)
                    return True
            # Default to public
            owner = u"PUBLIC"

        objectType = db.executeAll(guessInfoSql["typeFromNameAndOwner"], [name, owner])
        for type in objectType:
            if interactive:
                result.add(OraObject(owner, name, type[0]))
            else:
                self.setOwner(owner)
                self.setName(name)
                self.setType(type[0])
                self.guessStatus(db)
                return True

        # Try SYS objects
        owner = u"SYS"
        try:
            objectType = db.executeAll(guessInfoSql["typeFromNameAndSYS"], [name])
        except PysqlException:
            objectType = db.executeAll(guessInfoSql["typeFromNameAndOwner"], [name, owner])
        for type in objectType:
            if interactive:
                result.add(OraObject(owner, name, type[0]))
            else:
                self.setOwner(owner)
                self.setName(name)
                self.setType(type[0])
                self.guessStatus(db)
                return True

        # Try user, tablespace and so on
        for name in (self.getName(), self.getName().upper()):
            try:
                objectType = db.executeAll(guessInfoSql["otherTypeFromName"], [name])
            except PysqlException:
                objectType = []
            for type in objectType:
                if interactive:
                    result.add(OraObject(owner, name, type[0]))
                else:
                    self.setOwner(owner)
                    self.setName(name)
                    self.setType(type[0])
                    self.guessStatus(db)
                    return True

        if interactive:
            # If type is already defined, filter out object that does not match
            if self.getType():
                result = set([o for o in result if o.getType() == self.getType()])
            return result
        else:
            #Giving up.
            return False

    def getCreated(self, db):
        """@return: date of creation of the object"""
        if self.getOwner() == "":
            owner = db.getUsername().upper()
            result = db.executeAll(tabularSql["createdFromOwnerAndName"], [owner, self.getName()])
        else:
            try:
                result = db.executeAll(tabularSql["createdFromDBAAndName"],
                                     [self.getOwner(), self.getName()])
            except PysqlException:
                result = db.executeAll(tabularSql["createdFromOwnerAndName"],
                                     [self.getOwner(), self.getName()])
        if len(result) == 1:
            #TODO: use database encoding instead of just using str()
            return str(result[0][0])
        else:
            raise PysqlException(_("Cannot get the date of creation on object %s") % self.getName())

    def getLastDDL(self, db):
        """@return: date of last DDL modification of the object"""
        if self.getOwner() == "":
            owner = db.getUsername().upper()
            result = db.executeAll(tabularSql["lastDDLFromOwnerAndName"], [owner, self.getName()])
        else:
            try:
                result = db.executeAll(tabularSql["lastDDLFromDBAAndName"],
                                     [self.getOwner(), self.getName()])
            except PysqlException:
                result = db.executeAll(tabularSql["lastDDLFromOwnerAndName"],
                                     [self.getOwner(), self.getName()])
        if len(result) == 1:
            #TODO: use database encoding instead of just using str()
            return str(result[0][0])
        else:
            raise PysqlException(_("Cannot get the date of last DDL modification on object %s") % self.getName())

    def getDDL(self, db):
        """@return: SQL needed to create this object as a str"""
        if self.getType() == "":
            raise PysqlException(_("Object type is not defined"))
        if self.getOwner() == "":
            owner = db.getUsername().upper()
        else:
            owner = self.getOwner()
        result = db.executeAll(metadataSql["ddlFromTypeNameAndOwner"], [self.getType(), self.getName(), owner])
        if len(result) == 0:
            return None
        else:
            return result[0][0]

##############################################################################
class OraSegment(OraObject):
    """Father of tables and indexes"""
    def getTablespace(self, db):
        """@return: tablespace name that contains this segment"""
        raise PysqlNotImplemented()

class OraTabular(OraObject):
    """Father of tables, partitioned tables, views, materialized views. All objects that
    have rows and lines.
    The name is not very sexy. Anybody has a better choice?"""

    def __init__(self, objectOwner="", objectName=""):
        """Tabular object creation"""
        OraObject.__init__(self, objectOwner, objectName, "")

    def getRowCount(self, db):
        """@return: row count (select count(*) from ...)"""
        owner = self.getOwner()
        if owner == "":
            owner = db.getUsername().upper()
        return db.executeAll(u"""select count(*) from %s."%s" """ % (owner, self.getName()))[0][0]

    def getComment(self, db):
        """@return: db comment of the object"""
        if self.getOwner() == "":
            owner = db.getUsername().upper()
            result = db.executeAll(tabularSql["commentFromOwnerAndName"], [owner, self.getName()])
        else:
            try:
                result = db.executeAll(tabularSql["commentFromDBAAndName"],
                                     [self.getOwner(), self.getName()])
            except PysqlException:
                result = db.executeAll(tabularSql["commentFromOwnerAndName"],
                                     [self.getOwner(), self.getName()])
        if len(result) == 1:
            #TODO: use database encoding instead of just using str()
            return str(result[0][0])
        else:
            raise PysqlException(_("Cannot get the comment on object %s") % self.getName())

    def getTableColumns(self, db, sort=False):
        """Gets table or view columns
        @param sort: sort column in alphabetic order instead of Oracle order. Default is false
        @type sort: bool
        @return: array of column_name, columns_type, comments
        """
        if sort:
            sortCondition = " order by 1"
        else:
            sortCondition = ""

        if self.getOwner() == "":
            owner = db.getUsername().upper()
            columns = db.executeAll(tabularSql["columnsFromOwnerAndName"] + sortCondition,
                                  [owner, self.getName()])
        else:
            try:
                columns = db.executeAll(tabularSql["columnsFromDBAAndName"] + sortCondition,
                                      [self.getOwner(), self.getName()])
            except PysqlException:
                columns = db.executeAll(tabularSql["columnsFromOwnerAndName"] + sortCondition,
                                      [self.getOwner(), self.getName()])
        if len(columns) == 0:
            return (None, None, None)
        else:
            return columns

    def getNumberOfColumns(self, db):
        """@return: the number (int) of columns of the table/view"""
        if self.getOwner() == "":
            owner = db.getUsername().upper()
        return db.executeAll(tabularSql["numberOfColumnsFromOwnerAndName"],
                             [self.getOwner(), self.getName()])[0][0]

class OraDatafile(OraObject):
    """Datafile"""
    def __init__(self, datafileOwner="", datafileName=""):
        """Datafile creation"""
        OraObject.__init__(self, datafileOwner, datafileName, u"DATA FILE")

    def getTablespace(self, db):
        """@return: tablespace"""
        result = db.executeAll(datafileSql["tablespaceFromName"], [self.getName()])
        if result and result[0] and result[0][0]:
            return OraTablespace(tablespaceName=result[0][0])
        else:
            raise PysqlException(_("unable to get tablespace"))

    def getAllocatedBytes(self, db):
        """@return: number of bytes currently allocated in the data file"""
        result = db.executeAll(datafileSql["allocatedBytesFromName"], [self.getName()])
        if len(result) == 0:
            raise PysqlException(_("Data file %s does not exist") % self.getName())
        elif result[0][0] is None:
            msg = _("Insufficient privileges")
            raise PysqlException(msg)
        else:
            return int(result[0][0])

    def getFreeBytes(self, db):
        """@return: number of bytes currently free in the data file"""
        result = db.executeAll(datafileSql["freeBytesFromName"], [self.getName()])
        if len(result) == 0:
            raise PysqlException(_("Data file %s does not exist") % self.getName())
        else:
            return int(result[0][0])

    def guessStatus(self, db):
        """Guess datafile status"""
        status = db.executeAll(guessInfoSql["dbfStatusFromName"], [self.getName()])
        self.setStatus(status[0][0])

class OraDBLink(OraObject):
    """Database link"""
    def __init__(self, dbLinkOwner="", dbLinkName=""):
        """Directory creation"""
        OraObject.__init__(self, dbLinkOwner, dbLinkName, u"DATABASE LINK")

    def getRemoteHost(self, db):
        """@return: host of the db link"""
        if self.getOwner() == "":
            owner = db.getUsername().upper()
        else:
            owner = self.getOwner()
        result = db.executeAll(dbLinkSql["hostFromOwnerAndName"], [owner, self.getName()])
        if len(result) == 0:
            return ""
        else:
            return result[0][1]

    def getRemoteUser(self, db):
        """@return: user of the remote db"""
        if self.getOwner() == "":
            owner = db.getUsername().upper()
        else:
            owner = self.getOwner()
        result = db.executeAll(dbLinkSql["usernameFromOwnerAndName"], [owner, self.getName()])
        if len(result) == 0:
            return ""
        else:
            return result[0][1]

class OraDirectory(OraObject):
    """Oracle directory object"""
    def __init__(self, directoryOwner="", directoryName=""):
        """Directory creation"""
        OraObject.__init__(self, directoryOwner, directoryName, u"DIRECTORY")

    def getPath(self, db):
        """Gets the OS path of the directory object
        @return: full path (str)"""
        result = db.executeAll(directorySql["pathFromName"], [self.getName()])
        if len(result) == 0:
            return ""
        else:
            return result[0][0]

class OraIndex(OraSegment):
    """Oracle index"""
    def __init__(self, indexOwner="", indexName=""):
        """Index creation"""
        OraObject.__init__(self, indexOwner, indexName, u"INDEX")

    def getProperties(self, db):
        """Returns index following properties :
        Index_type, uniqueness, table_owner, table_name, compression, leaf_blocks, destincts_keys
        avg_lef_blocks_per_leys as a list of (property_name, property_value)"""
        if self.getOwner() == "":
            owner = db.getUsername().upper()
        else:
            owner = self.getOwner()
        result = db.executeAll(indexSql["propertiesFromOwnerAndName"], [owner, self.getName()])
        result.insert(0, db.getDescription())

        if not result:
            return None
        # Transpose the result
        result = [[result[i][j] for i in range(len(result))] for j in range(len(result[0]))]

        # Add indexed columns
        indexedColumns = self.getIndexedColumns(db)
        result.append([_("Indexed Columns"), ", ".join(["%s(%s)" % (i[0], i[1]) for i in indexedColumns])])

        return result

    def getTablespace(self, db):
        """Gets tablespace object
        @return: Returns object tablespace"""
        if self.getOwner() == "":
            owner = db.getUsername().upper()
        else:
            owner = self.getOwner()
        result = db.executeAll(indexSql["tablespaceFromOwnerAndName"], [owner, self.getName()])
        if result and result[0] and result[0][0]:
            return OraTablespace(tablespaceName=result[0][0])
        else:
            raise PysqlException(_("unable to get tablespace"))

    def getIndexedColumns(self, db):
        """Returns indexed columns as a list of (column_name, column_position)"""
        if self.getOwner() == "":
            owner = db.getUsername().upper()
        else:
            owner = self.getOwner()
        return db.executeAll(indexSql["indexedColumnsFromOwnerAndName"], [owner, self.getName()])

    def isPartitioned(self, db):
        """Gets True if the index is partitioned
        @return: true if index is partitioned, false otherwise"""
        if self.getOwner() == "":
            owner = db.getUsername().upper()
        else:
            owner = self.getOwner()
        result = db.executeAll(indexSql["isPartitionedFromOwnerAndName"], [owner, self.getName()])
        if len(result) == 0:
            return ""
        else:
            return (result[0][0] == "YES")

class OraMaterializedView(OraTabular, OraSegment):
    """Oracle materialized view"""
    def __init__(self, mviewOwner="", mviewName=""):
        """Materialized view creation"""
        OraObject.__init__(self, mviewOwner, mviewName, u"MATERIALIZED VIEW")

    def getSQL(self, db):
        """@return: SQL code behind the materialized view"""
        if self.getOwner() == "":
            owner = db.getUsername().upper()
        else:
            owner = self.getOwner()
        result = db.executeAll(mviewSql["queryFromOwnerAndName"], [owner, self.getName()])
        if len(result) == 0:
            return ""
        else:
            return result[0][1]

class OraStoredObject(OraObject):
    """Oracle package body, header for stored procedure and stored functions"""
    def getSQL(self, db):
        """Gets object SQL source code
        @return: source code (str)"""
        result = self.getSQLAsList(db)
        # Transform list of list of str to str
        return "".join(result)

    def getSQLAsList(self, db):
        """Gets object SQL source code
        @return: source code (list of str)"""
        if self.getType() == "":
            raise PysqlException("object type is not defined !")
        if self.getOwner() == "":
            owner = db.getUsername().upper()
        else:
            owner = self.getOwner()
        result = db.executeAll(storedObjectSql["sourceFromOwnerAndNameAndType"],
                                            [owner, self.getName(), self.getType()])
        return [i[0] for i in result]

    def setSQL(self, db, sql):
        """Sets the object SQL code.
        @arg sql: source code
        @type sql: str
        """
        raise PysqlNotImplemented()

    def _getSQL(self, db):
        """Common method used by getSQL and getSQLAsList"""

class OraProcedure(OraStoredObject):
    """Oracle stored procedure"""
    def __init__(self, procedureOwner, procedureName):
        OraObject.__init__(self, procedureOwner, procedureName, u"PROCEDURE")

    def getSource(self, db):
        """Gets source code
        @return: array of source line
        """
        if self.getOwner() == "":
            owner = db.getUsername().upper()
        else:
            owner = self.getOwner()
        source = db.executeAll(packageSql["sourceFromOwnerAndName"], [owner, self.getName()])
        if len(source) == 0:
            return (None)
        else:
            return source

class OraFunction(OraStoredObject):
    """Oracle stored function"""
    def __init__(self, procedureOwner, procedureName):
        OraObject.__init__(self, procedureOwner, procedureName, u"FUNCTION")

    def getSource(self, db):
        """Gets source code
        @return: array of source line
        """
        if self.getOwner() == "":
            owner = db.getUsername().upper()
        else:
            owner = self.getOwner()
        source = db.executeAll(packageSql["sourceFromOwnerAndName"], [owner, self.getName()])
        if len(source) == 0:
            return (None)
        else:
            return source

class OraPackage(OraStoredObject):
    """Oracle Package"""
    def __init__(self, packageOwner, packageName):
        OraObject.__init__(self, packageOwner, packageName, u"PACKAGE")

    def getProcedures(self, db):
        """Gets procedure names
        @return: array of procedure_name
        """
        if self.getOwner() == "":
            owner = db.getUsername().upper()
        else:
            owner = self.getOwner()
        columns = db.executeAll(packageSql["proceduresFromOwnerAndName"], [owner, self.getName()])
        if len(columns) == 0:
            return (None)
        else:
            return columns

    def getSource(self, db):
        """Gets source code
        @return: array of source line
        """
        if self.getOwner() == "":
            owner = db.getUsername().upper()
        else:
            owner = self.getOwner()
        source = db.executeAll(packageSql["sourceFromOwnerAndName"], [owner, self.getName()])
        if len(source) == 0:
            return (None)
        else:
            return source

class OraPackageBody(OraStoredObject):
    """Oracle stored package body"""
    def __init__(self, packageOwner, packageName):
        OraObject.__init__(self, packageOwner, packageName, u"PACKAGE BODY")

class OraSequence(OraObject):
    """Oracle sequence"""
    def __init__(self, sequenceOwner="", sequenceName=""):
        """Sequence creation"""
        OraObject.__init__(self, sequenceOwner, sequenceName, u"SEQUENCE")

    def getLast(self, db):
        """Gets the last value of the sequence object
        @return: full path (str)"""
        if self.getOwner() == "":
            owner = db.getUsername().upper()
        else:
            owner = self.getOwner()
        result = db.executeAll(sequenceSql["lastFromOwnerAndName"], [owner, self.getName()])
        if len(result) == 0:
            return ""
        else:
            return result[0][1]

    def getMin(self, db):
        """Gets the min value of the sequence object
        @return: full path (str)"""
        if self.getOwner() == "":
            owner = db.getUsername().upper()
        else:
            owner = self.getOwner()

        result = db.executeAll(sequenceSql["minFromOwnerAndName"], [owner, self.getName()])
        if len(result) == 0:
            return ""
        else:
            return result[0][1]

    def getMax(self, db):
        """Gets the max value of the sequence object
        @return: full path (str)"""
        if self.getOwner() == "":
            owner = db.getUsername().upper()
        else:
            owner = self.getOwner()
        result = db.executeAll(sequenceSql["maxFromOwnerAndName"], [owner, self.getName()])
        if len(result) == 0:
            return ""
        else:
            return result[0][1]

    def getStep(self, db):
        """Gets the step value of the sequence object
        @return: full path (str)"""
        if self.getOwner() == "":
            owner = db.getUsername().upper()
        else:
            owner = self.getOwner()
        result = db.executeAll(sequenceSql["stepFromOwnerAndName"], [owner, self.getName()])
        if len(result) == 0:
            return ""
        else:
            return result[0][1]

class OraSynonym(OraObject):
    """Oracle synonym"""
    def __init__(self, synonymOwner=u"PUBLIC", synonymName=""):
        """Synonym creation"""
        self.setName(synonymName)
        self.setOwner(synonymOwner)
        self.setType(u"SYNONYM")

    def getTarget(self, db, recursionStep=0):
        """Finds the oracle object targeted by this synonym.
        If the target is a synonym, recurse to find the real object.
        @return: Returns the synonym target as an OraObject object
        """
        recursionLimit = 4 # Maximum recursion allowed
        if self.getOwner() == "":
            owner = db.getUsername().upper()
        else:
            owner = self.getOwner()

        result = db.executeAll(synonymSql["targetFromOwnerAndName"], [owner, self.getName().upper()])
        if len(result) == 0:
            return None
        # if more than one synonym, takes the first (other public and equal)
        oraObject = OraObject(objectOwner=result[0][0], objectName=result[0][1])
        oraObject.guessInfos(db)

        if oraObject.getType() == "":
            raise PysqlActionDenied(_("Unable to resolve system synonyms"))
        elif oraObject.getType() == "SYNONYM":
            recursionStep += 1
            # Checks that we do not recurse too much
            if recursionStep > recursionLimit:
                print "[DEBUG] More than %d synonyms imbricated... Maybe a circular reference?" \
                        % recursionLimit
                return oraObject
            else:
                # Recurses to find the real target
                return oraObject.getTarget(db, recursionStep)
        else:
            return oraObject

class OraTable(OraTabular, OraSegment):
    """Oracle table"""
    def __init__(self, tableOwner="", tableName=""):
        """Table creation"""
        OraObject.__init__(self, tableOwner, tableName, u"TABLE")

    def getTablespace(self, db):
        """Gets tablespace name
        @return: Returns the name of the tablespace"""
        if self.getOwner() == "":
            owner = db.getUsername().upper()
        else:
            owner = self.getOwner()
        result = db.executeAll(tableSql["tablespaceFromOwnerAndName"], [owner, self.getName()])
        if result and result[0] and result[0][0]:
            return OraTablespace(tablespaceName=result[0][0])
        else:
            raise PysqlException(_("unable to get tablespace"))

    def getIndexedColumns(self, db):
        """Gets all table's indexed columns
        @return: array with column_name, index_name and index_position"""
        if self.getOwner() == "":
            owner = db.getUsername().upper()
        else:
            owner = self.getOwner()
        result = db.executeAll(tableSql["indexedColFromOwnerAndName"], [owner, self.getName()])
        return result

    def getPrimaryKeys(self, db):
        """Gets table primary key column name
        @return: list of columns used in primary key. Empty list if not PK found"""
        if self.getOwner() == "":
            owner = db.getUsername().upper()
        else:
            owner = self.getOwner()

        result = db.executeAll(tableSql["primaryKeyFromOwnerAndName"], [owner, self.getName()])
        if result:
            return [i[0] for i in result]
        else:
            return None

    def getLastAnalyzed(self, db):
        """Gets date of last statistics computation"""
        if self.getOwner() == "":
            owner = db.getUsername().upper()
        else:
            owner = self.getOwner()
        result = db.executeAll(tableSql["lastAnalyzedFromOwnerAndName"], [owner, self.getName()])
        if len(result) == 0:
            return ""
        else:
            return result[0][0]

    def getNumRows(self, db):
        """Gets number of rows from table's statistics"""
        if self.getOwner() == "":
            owner = db.getUsername().upper()
        else:
            owner = self.getOwner()
        result = db.executeAll(tableSql["numRowsFromOwnerAndName"], [owner, self.getName()])
        if len(result) == 0:
            return ""
        else:
            return result[0][0]

    def getAvgRowLength(self, db):
        """Gets average length of a single row from table's statistics"""
        if self.getOwner() == "":
            owner = db.getUsername().upper()
        else:
            owner = self.getOwner()
        result = db.executeAll(tableSql["avgRowLengthFromOwnerAndName"], [owner, self.getName()])
        if len(result) == 0:
            return ""
        else:
            return result[0][0]

    def getUsedBlocks(self, db):
        """Gets number of used blocks from table's statistics"""
        if self.getOwner() == "":
            owner = db.getUsername().upper()
        else:
            owner = self.getOwner()
        result = db.executeAll(tableSql["usedBlocksFromOwnerAndName"], [owner, self.getName()])
        if len(result) == 0:
            return ""
        else:
            return result[0][0]

    def getNeededBlocks(self, db):
        """Gets number of really used blocks from rowids"""
        if self.getOwner() == "":
            owner = db.getUsername().upper()
        else:
            owner = self.getOwner()
        result = db.executeAll(tableSql["neededBlocksFromOwnerAndName"] % (owner, self.getName()))
        if len(result) == 0:
            return ""
        else:
            return result[0][0]

    def isPartitioned(self, db):
        """Gets True if the table is partitioned
        @return: true if table is partitioned, false otherwise"""
        if self.getOwner() == "":
            owner = db.getUsername().upper()
        else:
            owner = self.getOwner()
        result = db.executeAll(tableSql["isPartitionedFromOwnerAndName"], [owner, self.getName()])
        if len(result) == 0:
            return ""
        else:
            return (result[0][0] == "YES")

class OraTablespace(OraObject):
    """Tablespace"""

    def __init__(self, tablespaceOwner="", tablespaceName=""):
        """Tablespace creation"""
        OraObject.__init__(self, tablespaceOwner, tablespaceName, u"TABLESPACE")
        self.datafiles = []

    def updateDatafileList(self, db):
        """Gets list of the data files which compose the tablespace"""
        self.datafiles = []
        if self.getName() != "":
            datafileNameList = db.executeAll(tablespaceSql["datafilesFromName"], [self.getName()])
            if len(datafileNameList) == 0:
                # Tries upper case
                self.setName(self.getName().upper())
                datafileNameList = db.executeAll(tablespaceSql["datafilesFromName"], [self.getName()])
                if len(datafileNameList) == 0:
                    return
            # Transposes datafile names vector
            datafileNames = [i[0] for i in datafileNameList]
            # Fills data file list
            for fileName in datafileNames:
                self.datafiles.append(OraDatafile("", fileName))

    def getAllocatedBytes(self, db):
        """@return: number of bytes currently allocated in the tablespace"""
        nbBytes = 0
        for datafile in self.datafiles:
            nbBytes += datafile.getAllocatedBytes(db)
        return nbBytes

    def getFreeBytes(self, db):
        """@return: number of bytes currently free in the tablespace"""
        nbBytes = 0
        for datafile in self.datafiles:
            nbBytes += datafile.getFreeBytes(db)
        return nbBytes

    def getDatafiles(self):
        """@return: list of datafiles (updateDatafileList must be called before !)"""
        return self.datafiles

    def guessStatus(self, db):
        """guess tablespace status"""
        status = db.executeAll(guessInfoSql["tbsStatusFromName"], [self.getName()])
        self.setStatus(status[0][0])


class OraTrigger(OraObject):
    """Trigger"""

    def __init__(self, triggerOwner="", triggerName=""):
        """Trigger creation"""
        OraObject.__init__(self, triggerOwner, triggerName, u"TRIGGER")
        self.table = None

    def updateTable(self, db):
        """Gets the triggered table"""
        self.table = None
        if self.getOwner() == "":
            owner = db.getUsername().upper()
        else:
            owner = self.getOwner()
        result = db.executeAll(triggerSql["tableFromOwnerAndName"], [owner, self.getName()])
        self.table = OraTable(tableOwner=result[0][0], tableName=result[0][1])

    def getBody(self, db):
        """@return: trigger body"""
        if self.getOwner() == "":
            owner = db.getUsername().upper()
        else:
            owner = self.getOwner()
        result = db.executeAll(triggerSql["bodyFromOwnerAndName"], [owner, self.getName()])
        if len(result) == 0:
            return ""
        else:
            return result[0][0]

    def getEvent(self, db):
        """@return: trigger type (BEFORE/AFTER, STATEMENT/ROW)"""
        if self.getOwner() == "":
            owner = db.getUsername().upper()
        else:
            owner = self.getOwner()
        result = db.executeAll(triggerSql["eventFromOwnerAndName"], [owner, self.getName()])
        if len(result) == 0:
            return ""
        else:
            return result[0][0]

    def getStatus(self, db):
        """@return: trigger status (ENABLED/DISABLED)"""
        if self.getOwner() == "":
            owner = db.getUsername().upper()
        else:
            owner = self.getOwner()
        result = db.executeAll(triggerSql["statusFromOwnerAndName"], [owner, self.getName()])
        if len(result) == 0:
            return ""
        else:
            return result[0][0]

    def getTable(self, db):
        """@return: triggered table (OraTable)"""
        if self.table is None:
            self.updateTable(db)
        return self.table

    def getTriggerType(self, db):
        """@return: triggering event (INSERT, DELETE or UPDATE)"""
        if self.getOwner() == "":
            owner = db.getUsername().upper()
        else:
            owner = self.getOwner()
        result = db.executeAll(triggerSql["typeFromOwnerAndName"], [owner, self.getName()])
        if len(result) == 0:
            return ""
        else:
            return result[0][0]

class OraUser(OraObject):
    """User"""
    def __init__(self, userOwner="", userName=""):
        """Directory creation"""
        OraObject.__init__(self, userOwner, userName, u"USER")
        self.tablespaces = []

    def updateTablespaceList(self, db):
        """Gets list of the tablespace which stores user segments"""
        self.tablespaces = []
        if self.getName() != "":
            tablespaceNameList = db.executeAll(userSql["tablespaceFromName"], [self.getName()])
            if len(tablespaceNameList) == 0:
                # Tries upper case
                self.setName(self.getName().upper())
                tablespaceNameList = db.executeAll(userSql["tablespaceFromName"], [self.getName()])
                if len(tablespaceNameList) == 0:
                    return
            # Transposes datafile names vector
            tablespaceNames = [i[0] for i in tablespaceNameList]
            # Fills data file list
            for tablespaceName in tablespaceNames:
                self.tablespaces.append(OraTablespace("", tablespaceName))

    def getTablespaces(self):
        """@return: list of tablespaces (updateTablespaceList must be called before !)"""
        return self.tablespaces

    def getDefaultTablespace(self, db):
        """@return: default tablespace name of the user"""
        self.setName(self.getName().upper())
        result = db.executeAll(userSql["defaultTbsFromName"], [self.getName()])
        if len(result) == 0:
            return ""
        else:
            return result[0][0]

    def getTempTablespace(self, db):
        """@return: temporary tablespace name of the user"""
        self.setName(self.getName().upper())
        result = db.executeAll(userSql["tempTbsFromName"], [self.getName()])
        if len(result) == 0:
            return ""
        else:
            return result[0][0]

    def getNbTables(self, db, tablespace=u"%"):
        """@return: number of tables owned by the user"""
        self.setName(self.getName().upper())
        result = db.executeAll(userSql["nbTablesFromNameAndTbs"], [self.getName(), tablespace])
        if len(result) == 0:
            return ""
        else:
            return result[0][0]

    def getNbIndexes(self, db, tablespace=u"%"):
        """@return: number of indexes owned by the user"""
        self.setName(self.getName().upper())
        result = db.executeAll(userSql["nbIndexesFromNameAndTbs"], [self.getName(), tablespace])
        if len(result) == 0:
            return ""
        else:
            return result[0][0]

    def guessStatus(self, db):
        """Guess user status"""
        status = db.executeAll(guessInfoSql["userStatusFromName"], [self.getName()])
        self.setStatus(status[0][0])

class OraView(OraTabular):
    """Oracle view"""
    def __init__(self, viewOwner="", viewName=""):
        """View creation"""
        OraObject.__init__(self, viewOwner, viewName, u"VIEW")

    def getSQL(self, db):
        """@return: SQL code behind the view"""
        if self.getOwner() == "":
            owner = db.getUsername().upper()
        else:
            owner = self.getOwner()
        result = db.executeAll(viewSql["queryFromOwnerAndName"], [owner, self.getName()])
        if len(result) == 0:
            return ""
        else:
            return result[0][1]

    def setSQL(self, db, sql):
        """@return: True if succeeded in editing SQL code behind the view, False otherwise"""
        if sql == "":
            raise PysqlException(_("SQL code of the view cannot be empty"))
        if self.getOwner() == "":
            db.execute(viewSql["replaceQueryFromName"] % (self.getName(), sql), fetch=False)
        else:
            db.execute(viewSql["replaceQueryFromFullName"] % (self.getFullName(), sql), fetch=False)
