# -*- coding: utf-8 -*-

""" Database related stuff: Oracle interface (PysqlDb)
and backgound queries (BgQuery)
@author: Sébastien Renard (sebastien.renard@digitalfox.org)
@license: GNU GPL V3
"""

# pylint: disable-msg=E0611

# Python imports:
from cx_Oracle import connect, DatabaseError, InterfaceError, LOB, STRING, SYSDBA, SYSOPER
import sys
from threading import Thread
from datetime import datetime, timedelta, date

# Pysql imports:
from .pysqlexception import PysqlException, PysqlActionDenied, PysqlNotImplemented
from .pysqlconf import PysqlConf
from .pysqlcolor import BOLD, CYAN, GREEN, GREY, RED, RESET
from .pysqlhelpers import warn

# Aditionnal cx_Oracle Import
CX_STARTUP_SHUTDOWN = True
try:
    from cx_Oracle import PRELIM_AUTH, DBSHUTDOWN_ABORT, DBSHUTDOWN_IMMEDIATE, DBSHUTDOWN_TRANSACTIONAL, DBSHUTDOWN_FINAL
except ImportError:
    CX_STARTUP_SHUTDOWN = False
    PRELIM_AUTH = 0  # Means that PRELIM_AUTH is not used.


class PysqlDb:
    """ Handles database interface"""
    MAXIMUM_FETCH_SIZE = 10000  # Maximum size of a result set to fetch in one time
    FETCHALL_FETCH_SIZE = 30  # Size of cursor for fetching all type queries

    def __init__(self, connectString, mode=""):
        # Instance attributs
        self.connection = None
        self.cursor = None

        # Read Conf
        self.conf = PysqlConf.getConfig()

        # Keep connection string to allow future connection
        self.connectString = connectString

        # Connect to Oracle
        try:
            if mode == "sysoper":
                try:
                    self.connection = connect(self.connectString, mode=SYSOPER, threaded=True)
                except (DatabaseError) as e:
                    print(CYAN + _("Connected to an idle instance") + RESET)
                    self.connection = connect(self.connectString, mode=SYSOPER | PRELIM_AUTH, threaded=True)
            elif mode == "sysdba":
                try:
                    self.connection = connect(self.connectString, mode=SYSDBA, threaded=True)
                except (DatabaseError) as e:
                    print(CYAN + _("Connected to an idle instance") + RESET)
                    self.connection = connect(self.connectString, mode=SYSDBA | PRELIM_AUTH, threaded=True)
            else:
                self.connection = connect(self.connectString, threaded=True)
        except (DatabaseError, RuntimeError, InterfaceError) as e:
            raise PysqlException(_("Cannot connect to Oracle: %s") % e)

    def startup(self, mode="normal"):
        """Starts up Oracle instance"""
        if not CX_STARTUP_SHUTDOWN:
            raise PysqlException(_("Your Oracle and/or cx_Oracle version is too old to support startup option"))
        try:
            self.connection.startup()
            self.connection = connect("/", mode=SYSDBA, threaded=True)
            self.cursor = self.connection.cursor()
            self.cursor.execute("alter database mount")
            if mode == "normal":
                self.cursor.execute("alter database open")
        except DatabaseError as e:
            raise PysqlException(_("Cannot start instance up: %s") % e)

    def shutdown(self, mode="normal"):
        """Shuts down Oracle instance"""
        if not CX_STARTUP_SHUTDOWN:
            raise PysqlException(_("Your Oracle and/or cx_Oracle version is too old to support shutdown option"))

        try:
            if mode == "abort":
                self.connection.shutdown(mode=DBSHUTDOWN_ABORT)
            elif mode == "immediate":
                self.connection.shutdown(mode=DBSHUTDOWN_IMMEDIATE)
                self.connection.shutdown(mode=DBSHUTDOWN_FINAL)
            else:
                self.connection.shutdown(mode=DBSHUTDOWN_TRANSACTIONAL)
                self.connection.shutdown(mode=DBSHUTDOWN_FINAL)
            self.connection = connect("/", mode=SYSDBA | PRELIM_AUTH, threaded=True)
        except DatabaseError as e:
            raise PysqlException(_("Cannot shut instance down: %s") % e)

    def commit(self):
        """Commit pending transaction"""
        try:
            self.connection.commit()
        except DatabaseError as e:
            raise PysqlException(_("Cannot commit: %s") % e)

    def rollback(self):
        """Rollback pending transaction"""
        try:
            self.connection.rollback()
        except DatabaseError as e:
            raise PysqlException(_("Cannot rollback: %s") % e)

    def executeAll(self, sql, param=[]):
        """Executes the request given in parameter and
        returns a list of record (a cursor.fetchall())
        Use a private cursor not to pollute execute on.
        So the getDescription does not work for executeAll"""
        try:
            if self.cursor is None:
                self.cursor = self.connection.cursor()
            self.cursor.arraysize = self.FETCHALL_FETCH_SIZE
            if param == []:
                self.cursor.execute(sql)
            else:
                self.cursor.prepare(sql)
                self.cursor.execute(None, param)
            return self.cursor.fetchall()
        except (DatabaseError, InterfaceError) as e:
            raise PysqlException(_("Cannot execute query: %s") % e)

    def execute(self, sql, fetch=True, cursorSize=None):
        """Executes the request given in parameter.

         For a select request, returns a list of record and a flag to indicate if there's more record
         For insert/update/delete, return the number of record processed
         @param fetch: for select queries, start fetching (default is true)
         @param cursorSize: if defined, overide the config cursor size"""
        if not sys.stdin.isatty():
            fetch = False
        try:
            if self.cursor is None:
                self.cursor = self.connection.cursor()
            if cursorSize:
                self.cursor.arraysize = cursorSize
            else:
                self.cursor.arraysize = self.conf.get("fetchSize")
            self.cursor.execute(sql)
            if sql.upper().startswith("SELECT") and fetch:
                return self.fetchNext()
            elif sql.upper().startswith("SELECT") and not fetch:
                return (self.cursor.fetchall(), False)
            else:
                return self.getRowCount()
        except (DatabaseError, InterfaceError) as e:
            raise PysqlException(_("Cannot execute query: %s") % e)

    def validate(self, sql):
        """Validates the syntax of the DML query given in parameter.
        @param sql: SQL query to validate
        @return: None but raise PysqlException if sql cannot be validated"""
        try:
            if self.cursor is None:
                self.cursor = self.connection.cursor()
            self.cursor.arraysize = 1
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
        except (DatabaseError, InterfaceError) as e:
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
                return [i[0] + " (" + i[1].__name__ + ")" for i in self.cursor.description]

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
            moreRows = False
            if self.cursor is not None:
                if nbLines <= 0:
                    # Ok, default value or stupid value. Using Cursor array size
                    nbLines = self.cursor.arraysize
                elif nbLines > self.MAXIMUM_FETCH_SIZE:
                    # Don't fetch too much!
                    nbLines = self.MAXIMUM_FETCH_SIZE

                result = self.cursor.fetchmany(nbLines)
                if len(result) == nbLines:
                    moreRows = True
                return (result, moreRows)
            else:
                raise PysqlException(_("No result set. Execute a query before fetching result !"))
        except (DatabaseError, InterfaceError) as e:
            raise PysqlException(_("Error while fetching results: %s") % e)

    def getServerOuput(self):
        """Gets the server buffer output filled with dbms_output.put_line
        dbms_output should be enabled (should we do this automatically at cursor creation ?)
        Return list of string or empty list [] if there's nothing to get."""
        if not self.cursor:
            return
        result = []
        serverOutput = self.cursor.var(STRING)
        serverRC = self.cursor.var(STRING)
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
        return str(self.connection.username)

    def getDSN(self):
        """Gets the database service name
        @return: databse service name (unicode)"""
        return str(self.connection.dsn)

    def getConnectString(self):
        """Gets the connection string used to create this instance
        @return: connect string (unicode)"""
        return self.connectString

    def getVersion(self):
        """Gets the version number of the database server
        @return: db server version (unicode)"""
        return str(self.connection.version)

    def close(self):
        """Releases object connection"""
        # self.cursor.close()
        try:
            self.connection.close()
        except (DatabaseError, InterfaceError) as e:
            raise PysqlException(_("Cannot close connection: %s") % e)


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
        self.db = PysqlDb(connect_string)
        self.query = query
        self.exceptions = exceptions
        self.result = None
        self.moreRows = False
        self.error = _("None")
        Thread.__init__(self)
        self.setDaemon(True)

    def run(self):
        """Method executed when the thread object start() method is called"""
        try:
            (self.result, self.moreRows) = self.db.execute(self.query)
        except PysqlException as e:
            self.error = str(e)
            self.exceptions.append(e)
            self.result = None
            self.moreRows = False

    def getName(self):
        """Return a simple name: the ID of the python thread"""
        return Thread.getName(self).split("-")[1]

    def getStartTime(self):
        pass

    def getEndTime(self):
        pass

    def getExecutionTime(self):
        pass

