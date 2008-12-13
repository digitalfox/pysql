#!/usr/bin/python
# -*- coding: utf-8 -*-

# Sébastien Renard (sebastien.renard@digitalfox.org)
# Code licensed under GNU GPL V2

""" Database related stuff: Oracle interface (PysqlDb)
and backgound queries (BgQuery)"""

# pylint: disable-msg=E0611

#Python imports:
from cx_Oracle import connect, DatabaseError, InterfaceError, LOB, STRING, SYSDBA, SYSOPER
from threading import Thread
from datetime import datetime, date

# Pysql imports:
from pysqlexception import PysqlException, PysqlActionDenied, PysqlNotImplemented
from pysqlconf import PysqlConf
from pysqlcolor import BOLD, CYAN, GREEN, GREY, RED, RESET
from pysqlhelpers import warn

class PysqlDb:
    """ Handles database interface"""
    MAXIMUM_FETCH_SIZE=10000      # Maximum size of a result set to fetch in one time
    FETCHALL_FETCH_SIZE=30        # Size of cursor for fetching all type queries

    def __init__(self, connectString, mode=""):
        # Instance attributs
        self.connection=None
        self.cursor=None

        # Keep connection string to allow future connection
        self.connectString=connectString
        
        # Read Conf
        self.conf=PysqlConf.getConfig()

        # Connect to Oracle
        try:
            if mode=="sysoper":
                self.connection=connect(connectString, mode=SYSOPER)
            elif mode=="sysdba":
                self.connection=connect(connectString, mode=SYSDBA)
            else:
                self.connection=connect(connectString)
        except (DatabaseError, RuntimeError), e:
            raise PysqlException(_("Cannot connect to Oracle: %s") % e)


    def commit(self):
        """Commit pending transaction"""
        try:
            self.connection.commit()
        except DatabaseError, e:
            raise PysqlException(_("Cannot commit: %s") % e)

    def rollback(self):
        """Rollback pending transaction"""
        try:
            self.connection.rollback()
        except DatabaseError, e:
            raise PysqlException(_("Cannot rollback: %s") % e)

    def executeAll(self, sql, param=[]):
        """Executes the request given in parameter and
        returns a list of record (a cursor.fetchall())
        Use a rpivate cursor not to pollute execute on.
        So the getDescription does not work for executeAll"""
        sql=self.encodeSql(sql)
        param=self.encodeSql(param)
        try:
            if self.cursor is None:
                self.cursor=self.connection.cursor()
            self.cursor.arraysize=self.FETCHALL_FETCH_SIZE
            if param==[]:
                self.cursor.execute(sql)
            else:
                self.cursor.prepare(sql)
                self.cursor.execute(None, param)
            return self.decodeData(self.cursor.fetchall())
        except (DatabaseError, InterfaceError), e:
            raise PysqlException(_("Cannot execute query: %s") % e)

    def execute(self, sql, fetch=True, cursorSize=None):
        """Executes the request given in parameter.

         For a select request, returns a list of record and a flag to indicate if there's more record
         For insert/update/delete, return the number of record processed
         @param fetch: for select queries, start fetching (default is true)
         @param cursorSize: if defined, overide the config cursor size"""
        sql=self.encodeSql(sql)
        try:
            if self.cursor is None:
                self.cursor=self.connection.cursor()
            if cursorSize:
                self.cursor.arraysize=cursorSize
            else:
                self.cursor.arraysize=self.conf.get("fetchSize")
            self.cursor.execute(sql)
            if sql.upper().startswith("SELECT") and fetch:
                return self.fetchNext()
            else:
                return self.getRowCount()
        except (DatabaseError, InterfaceError), e:
            raise PysqlException(_("Cannot execute query: %s") % e)

    def validate(self, sql):
        """Validates the syntax of the DML query given in parameter.
        @param sql: SQL query to validate
        @return: None but raise PysqlException if sql cannot be validated"""
        sql=self.encodeSql(sql)
        try:
            if self.cursor is None:
                self.cursor=self.connection.cursor()
            self.cursor.arraysize=1
            if sql.upper().startswith("SELECT"):
                self.cursor.execute(sql)
                return True
            elif (sql.upper().startswith("INSERT")
               or sql.upper().startswith("UPDATE")
               or sql.upper().startswith("DELETE")):
                self.connection.begin()
                self.cursor.execute(sql)
                self.connection.rollback()
                return True
            else:
                raise PysqlException(_("Can only validate DML queries"))
        except (DatabaseError, InterfaceError), e:
            raise PysqlException(_("Cannot validate query: %s") % e)

    def getCursor(self):
        """Returns the cursor of the current query"""
        return self.cursor

    def getDescription(self, short=True):
        """Returns header description of cursor with column name and type
        If short is set to false, the type is given after the column name"""
        if self.cursor is not None:
            if short:
                return [i[0] for i in self.cursor.description]
            else:
                return [i[0]+" ("+i[1].__name__+")" for i in self.cursor.description]

    def getRowCount(self):
        """Returns number of line processed with last request"""
        if self.cursor is not None:
            return self.cursor.rowcount
        else:
            return 0

    def fetchNext(self, nbLines=0):
        """Fetches nbLines from current cursor.
        Returns a list of record and a flag to indicate if there's more record"""
        try:
            moreRows=False
            if self.cursor is not None:
                if nbLines<=0:
                    # Ok, default value or stupid value. Using Cursor array size
                    nbLines=self.cursor.arraysize
                elif nbLines>self.MAXIMUM_FETCH_SIZE:
                    # Don't fetch too much!
                    nbLines=self.MAXIMUM_FETCH_SIZE

                result=self.cursor.fetchmany(nbLines)
                if len(result)==nbLines:
                    moreRows=True
                return (self.decodeData(result), moreRows)
            else:
                raise PysqlException(_("No result set. Execute a query before fetching result !"))
        except (DatabaseError, InterfaceError), e:
            raise PysqlException(_("Error while fetching results: %s") % e)

    def getServerOuput(self):
        """Gets the server buffer output filled with dbms_output.put_line
        dbms_output should be enabled (should we do this automatically at cursor creation ?)
        Return list of string or empty list [] if there's nothing to get."""
        if not self.cursor:
            return
        result=[]
        serverOutput=self.cursor.var(STRING)
        serverRC=self.cursor.var(STRING)
        while True:
            self.cursor.execute("""begin dbms_output.get_line(:x,:y); end;""",
                                [serverOutput, serverRC])
            if serverOutput.getvalue():
                result.append(serverOutput.getvalue())
            else:
                break
        return result

    def getUsername(self):
        """Gets the name of the user connected to the database
        @return: username (unicode)"""
        return unicode(self.connection.username)

    def getDSN(self):
        """Gets the database service name
        @return: databse service name (unicode)"""
        return unicode(self.connection.dsn)

    def getConnectString(self):
        """Gets the connection string used to create this instance
        @return: connect string (unicode)"""
        return self.connectString

    def getVersion(self):
        """Gets the version number of the database server
        @return: db server version (unicode)"""
        return unicode(self.connection.version)

    def close(self):
        """Releases object connection"""
        #self.cursor.close()
        try:
            self.connection.close()
        except (DatabaseError, InterfaceError), e:
            raise PysqlException(_("Cannot close connection: %s") % e)

    def encodeSql(self, sql):
        """Encode sql request in the proper encoding.
        @param sql: sql request in unicode format or list of unicode string
        @return: sql text encoded
        """
        if self.connection:
            encoding=self.connection.nencoding
        else:
            raise PysqlException("Cannot encode data, not connected to Oracle")
        if sql is None:
            return None
        if isinstance(sql, list):
            # Recurse to encode each item
            return [self.encodeSql(i) for i in sql]

        if isinstance(sql, str):
            warn("string '%s' is already encoded" % sql)
            return sql
        try:
            sql=sql.encode(encoding)
        except UnicodeEncodeError:
            sql=sql.encode(encoding, "replace")
            warn("Got unicode error while encoding '%s'" % sql) 
        return sql

    def decodeData(self, data):
        """Encode data fetch out database to unicode
        @param data: str or list or str
        @return: encoded data"""
        #TODO: factorise code with encodeSql function
        if self.connection:
            encoding=self.connection.nencoding
        else:
            raise PysqlException("Cannot decode data, not connected to Oracle")
        if data is None:
            return u"NULL"
        elif isinstance(data, (list, tuple)):
            # Recurse to decode each item
            return [self.decodeData(i) for i in data]
        elif isinstance(data, (int, float)):
            # Nothing to do
            return data
        elif isinstance(data, datetime):
            #TODO: use user define format or Oracle settings
            data=data.strftime("%Y/%m/%d %H:%M:%S")
        elif isinstance(data, date):
            #TODO: use user define format or Oracle settings
            data=data.strftime("%Y/%m/%d")
        elif isinstance(data, LOB):
            data=data.read(1, data.size())
        elif isinstance(data, unicode):
            warn("Warning, string '%s' is already Unicode" % data)
            return data

        # Decode data
        try:
            data=data.decode(encoding)
        except UnicodeDecodeError:
            data=data.decode(encoding, "ignore")
            warn("Can't decode '%s' with %s codec. Check your NLS_LANG variable" % (data, encoding))
        except AttributeError:
            warn("Cannot decode %s object" % type(data))
        return data


class BgQuery(Thread):
    """Background query to Oracle"""
    def __init__(self, connect_string, query, exceptions):
        """
        @param connect_string: Oracle connection string to database
        @type connect_string: str
        @param query: SQL request to be executed in backgound
        @type query: str
        @param exceptions: list of current exception to sum up error at exit
        @type exceptions: list
        """
        self.db=PysqlDb(connect_string)
        self.query=query
        self.exceptions=exceptions
        self.result=None
        self.moreRows=False
        self.error=_("No")
        Thread.__init__(self)
        self.setDaemon(True)

    def run(self):
        """Method executed when the thread object start() method is called"""
        try:
            (self.result, self.moreRows)=self.db.execute(self.query)
        except PysqlException, e:
            self.error=unicode(e)
            self.exceptions.append(e)
            self.result=None
            self.moreRows=False

    def getName(self):
        """Return a simple name: the ID of the python thread"""
        return Thread.getName(self).split("-")[1]

    def getStartTime(self):
        pass

    def getEndTime(self):
        pass

    def getExecutionTime(self):
        pass

