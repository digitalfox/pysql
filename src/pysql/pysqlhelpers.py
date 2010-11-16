#!/usr/bin/python
# -*- coding: utf-8 -*-

"""This module defines some common useful helper functions
@author: Sébastien Renard (sebastien.renard@digitalfox.org)
@license: GNU GPL V3
"""

# Python imports:
import os
import sys
import traceback
from re import match, sub
import datetime
from cStringIO import StringIO
from time import sleep
from threading import Thread, Lock
try:
    from cx_Oracle import LOB
except:
    pass
try:
    import setproctitle
    HAVE_SETPROCTITLE = True
except ImportError:
    HAVE_SETPROCTITLE = False


# Pysql imports:
from pysqlexception import PysqlException, PysqlActionDenied
from pysqlcolor import BOLD, CYAN, GREEN, GREY, RED, RESET
import pysqlupdate

# Help functions
def addWildCardIfNeeded(aString, wildcard="%"):
    """If aString does not have any wildcard, add one at the begining and one at the end"""
    if not aString.count(wildcard):
        return wildcard + aString + wildcard
    else:
        return aString

def colorDiff(diff):
    """Transforms poorly readable ndiff output into colored diff
    @arg diff: generator returned by difflib.ndiff() function
    @return: list of string diffs with color to highlight diff
    """
    result = []
    for item in diff:
        if item[0] == "?": # Get diff hint to colorise the previous line
            previous = result[-1] # The line above we want to colorise
            i = 0
            coloring = False # flag to start/stop coloring
            newPrevious = [] # the new previous line with color
            for character in item:
                if character == "\n":
                    # End of change. Add end of previous
                    newPrevious.append(previous[i:])
                else:
                    if character in ("-", "^", "+"):
                        if not coloring:
                            newPrevious.append(RED)
                            coloring = True
                    else:
                        if coloring:
                            newPrevious.append(RESET)
                            coloring = False
                    newPrevious.append(previous[i])
                i += 1
            newPrevious.append(RESET) # Always stop color at end of line
            result[-1] = "".join(newPrevious) # Create new colorize line
        else:
            result.append(item) # Just store simple line (equal, + or -)
    return result


def convert(value, unit):
    """Converts an number in Bytes into a bigger unit.
       Beware of any data loss"""
    unit = unit.lower()
    if unit == "b":
        return value
    elif unit == "kb":
        return float(value) / 1024
    elif unit == "mb":
        return float(value) / 1024 / 1024
    elif unit == "gb":
        return float(value) / 1024 / 1024 / 1024
    elif unit == "tb":
        return float(value) / 1024 / 1024 / 1024 / 1024
    elif unit == "pb":
        return float(value) / 1024 / 1024 / 1024 / 1024 / 1024
    else:
        raise PysqlException(_("Unit not handled: %s") % unit)

def getProg(availables, given, default):
    """Checks if 'given' graphviz program is in the 'availables' list
    Raises an exception if program is not available or return the prog (default if given is 'auto'
    @arg availables: dict of graphviz availables program as return by find_graphivz()
    @arg given: program choose by user
    @arg default: program used if user choose default"""
    if given == "auto":
        given = default
    if not availables.has_key(given):
        raise PysqlActionDenied(given +
                                _(" is not installed. Get it at http://www.graphviz.org/Download.php"))
    else:
        return given

def itemLength(item):
    """Compute length of a result set item"""
    if item is None:
        return 0
    elif isinstance(item, (int, float, long, datetime.datetime, datetime.timedelta)):
        return len(str(item))
    elif isinstance(item, LOB):
        return item.size()
    else:
        return len(item)

def generateWhere(keyword, filterClause):
    """ Generate where clause from pysql syntax to filter Oracle object
    Pysql syntax : pattern1 or (pattern2 and pattern3). Pattern are all accepted Oracle like pattern
    @arg filter: pysql where clause syntax as a list of words
    @arg keyword: the database object name on which filter apply
    @return: SQL where clause"""
    result = []
    endingParenthisis = 0
    startsWithParenthisis = True
    lastWordWasOperand = True
    parenthisisBalance = 0
    for word in filterClause.split():
        # Keep and remove start & end parenthisis
        while word.startswith("("):
            parenthisisBalance += 1
            startsWithParenthisis = True
            result.append("(")
            word = word[1:]
        while word.endswith(")"):
            parenthisisBalance -= 1
            endingParenthisis += 1
            word = word[:-1]
        # Handle boolean operator
        if word.lower() in ("and", "or"):
            if startsWithParenthisis or lastWordWasOperand:
                # Operator at begin of phrase (just after parenthisis)
                # Or two operators following
                raise PysqlException(_("Operator %s was not expected at word %s") % (word.upper(), len(result) + 1))
            result.append(word.lower())
            lastWordWasOperand = True
            startsWithParenthisis = False
        # Construct like clause
        elif len(word) > 0 and lastWordWasOperand:
            if word.startswith("!"):
                if len(word) > 1 and word[1] == "(":
                    raise PysqlException(_("The ! is not supported before parenthisis"))
                operand = "not like"
                word = word[1:]
            else:
                operand = "like"
            lastWordWasOperand = False
            startsWithParenthisis = False
            result.append("%s %s '%s'" % (keyword, operand, word))
        elif len(word) > 0 and not lastWordWasOperand:
            # Terms of clause must be separted by operators
            raise PysqlException(_("Operator (AND/OR) expected at word %s") % (len(result) + 1))
        while endingParenthisis > 0:
            endingParenthisis -= 1
            result.append(")")
    if parenthisisBalance != 0:
        raise PysqlException(_("Unblanced parenthisis (%s)") % parenthisisBalance)
    return " ".join(result)

def removeComment(line, comment=False):
    """Removes SQL comments from line
    @arg line: SQL line from which we want to remove comment
    @arg comment: flag to indicate if we are in the middle of a multiline comment (default is false)
    @type line: str
    @type comment: bool
    @return: line modified (str) and a flag (bool) that indicate if we are in a multiline comment"""
    # Remove one line comment (-- or /* */)
    line = sub("\/\*\*\/", " ", line)         # Remove /**/ pattern
    line = sub("\/\*[^+|].*?\*\/", " ", line) # Remove /* ... */ except /*+ ... */
    line = sub("--[^+|].*$", "", line)        # Remove -- ... except --+ ...
    line = sub("--$", "", line)               # Remove -- at the end of line (stupid but allowed)

    if line == "--":
        return "", comment

    # Honors multi line SQL comments but do not shoot Oracle hint!
    # /* comment
    if match(".*/\*[^+].*", line) or match(".*/\*$", line):
        # Remove commented part
        line = sub("/\*[^+|].*", "", line)
        line = sub("/\*$", "", line) # previous regexp does not match */ at end of line
        # Starting multiline comment
        comment = True
    # comment */ (a /* was give before)
    elif match(".*\*\/.*", line) and comment:
        # Remove commented part
        line = sub(".*\*\/", "", line)
        # end for multiline comment
        comment = False
    elif comment:
        line = ""
    return (line, comment)

def which(progName):
    """Mimics the Unix which command
    @param progName: program name that will be search through PATH
    @return: full path to program or None if not find in PATH"""
    for directory in os.getenv("PATH").split(os.pathsep):
        fullpath = os.path.join(directory, progName)
        if os.access(fullpath, os.X_OK) and os.path.isfile(fullpath):
            return fullpath
    return None

def warn(message):
    """Just print a formated warning message on screen if PYSQL_WARNING env var is set (whatever value)
    @param message: unicode or str message. Conversion will done with print and default encoding
    """
    if os.environ.has_key("PYSQL_WARNING"):
        print "%s==>Warning:%s %s%s" % (RED, BOLD, message, RESET)

def printStackTrace():
    """Print stack trace with debug information"""
    # Just a hook for a more pleasant error handling
    print "------------------8<-------------------------------------"
    traceback.print_exc()
    print "------------------8<-------------------------------------"
    printComponentsVersion()
    print
    print RED + BOLD + "Please, send the text above to pysql@digitalfox.org" + RESET
    print

def printComponentsVersion():
    try:
        pysqlVersion = pysqlupdate.currentVersion()
    except PysqlException:
        pysqlVersion = RED + BOLD + "missing" + RESET
    try:
        import cx_Oracle
        cxVersion = cx_Oracle.version
    except Exception:
        cxVersion = RED + BOLD + "missing" + RESET
    print BOLD + "PySQL release: %s" % pysqlVersion + RESET
    print "    cx Oracle release: %s" % cxVersion
    print "    Python release: %s" % sys.version.replace("\n", " ")

def setTitle(title, codec):
    """Sets the window title and optionnaly process title
    @param title: window title
    @type title: unicode string
    @param codec: codec used to encode string"""
    if HAVE_SETPROCTITLE:
        setproctitle.setproctitle(title)

    if os.name == 'posix' and os.environ["TERM"] == 'xterm' and os.getenv("PYDEVDEBUG", "0") == "0":
        title = "\033]0;%s\007" % title
        sys.stdout.write(title.encode(codec, "replace"))
    elif os.name == "nt":
        os.system("title %s" % title.encode(codec, "replace"))

def getTitle():
    """Gets the window title
    @return: str"""
    if os.name == "posix":
        # Getting terminal title is.. a mess
        # An escape code (echo  -e '\e[21t') can get it
        # but is often disabled for safety reason...
        # Default to basic title
        title = "%s@%s" % (os.environ.get("USER", "user"), os.popen("hostname").readline().strip())
        if os.environ.has_key("DISPLAY"):
            # Use X windows to get title
            xtitle = os.popen("xprop -id $WINDOWID WM_NAME").readline().strip()
            if not ("WM_NAMEAborted" in title or "WM_NAMEAbandon" in title):
                try:
                    title = xtitle.split("=")[1].lstrip(' ').strip('"')
                except IndexError:
                    # DISPLAY is not correctly set
                    pass
    elif os.name == "nt":
        # Term title need pywin32 on windows... Too much deps for simple need
        # Using default name instead
        title = os.environ["ComSpec"]
    else:
        # Unknown OS
        title = "terminal"
    return title

def getTermWidth():
    """Gets the terminal width. Works only on Unix system.
    @return: terminal width or "120" is system not supported"""
    if os.name == "posix":
        result = os.popen("tput cols").readline().strip()
        if result:
            return int(result)
    else:
        # Unsupported system, use default 120
        return 120

def upperIfNoQuotes(aString):
    """Used for Oracle owner and name case policy
    @param aString: input string to parse
    @return: Upper case string if no quotes are given, else remove quotes and leave string as is"""
    if aString.startswith("'") or aString.startswith('"'):
        return aString.strip("'").strip('"')
    else:
        return aString.upper()


def getFromClause(line):
    """Extract the "from" clause of an sql request
    @param line: sql text
    @return: dictionary with key as alias (table name if no alias) and table as value"""

    tables = {} # alias/table
    fromClause = []
    inFrom = False
    for word in line.split():
        if word.lower() in ("where", "order", "group", "values", "set"):
            inFrom = False
        elif inFrom:
            if word.lower().lstrip("(") == "select":
                # Imbricated request
                #FIXME: too much simple. We need a real sql parser
                inFrom = False
            else:
                fromClause.append(word)
        elif word.lower() == "from":
            inFrom = True

    for tableDef in " ".join(fromClause).split(","):
        tableDef = tableDef.strip(";").strip(")").strip()
        if tableDef.count(" ") == 1:
            tableName, tableAlias = tableDef.split()
            tables[tableAlias] = tableName
        else:
            tables[tableDef] = tableDef

    return tables

def getKnownTablesViews(line, refList):
    """As getFromClause is much too simple, make something simplier:
    just extract names if a table or view have this name. No sql parsing at all...
    @param line: sql query
    @param refList: list of tables/view names to watch for"""
    result = set()
    for token in line.split():
        token = token.strip(",").strip(";").strip(")").strip()
        if "." in token:
            # Remove what could be a schema name
            token = token.split(".", 1)[1]
        if token in refList:
            result.add(token)
    return list(result)

def getLastKeyword(line):
    """@return: the last sql keyword of the line"""
    keywords = ["select", "update", "delete", # DML
                "alter", "create", "drop", # DDL
                "where", "order by", "group by", "having", "from", "into", # sql grammar
                "sum", "abs", "round", "upper", "lower", "set", # Functions
                "table", "index", "view", "synonym", "trigger", "tablespace", # objects
                "datafile", "columns", "user", "sequence"] # objects
    lastKeyword = None
    for token in line.lower().split():
        token = token.strip(",").strip(";").strip(")").strip("(").strip()
        if token in keywords:
            lastKeyword = token
    return lastKeyword

class WaitCursor(Thread):
    """A waiting cursor for long operation that
    catch output and flush it after waiting"""
    def __init__(self):
        self.state = "WAIT"
        self.lock = Lock()           # Lock used to synchronise IO and cursor stop
        Thread.__init__(self)

    def run(self):
        """Method executed when the thread object start() method is called"""

        realStdout = sys.stdout # Backup stdout
        tmpStdout = StringIO()  # Store here all data output during waiting state
        sys.stdout = tmpStdout  # Capture stdout
        cursorState = ("-", "\\", "|", "/")
        i = 0
        self.lock.acquire()
        while self.state == "WAIT":
            realStdout.write(cursorState[i % 4])
            realStdout.flush()
            sleep(0.1)
            realStdout.write("\b")
            i += 1

        # Restore standard output and print temp data
        sys.stdout = realStdout
        sys.stdout.write(tmpStdout.getvalue())
        sys.stdout.flush()
        self.lock.release()

    def stop(self):
        self.state = "STOP"
        self.lock.acquire() # Wait end of IO flush before returning
