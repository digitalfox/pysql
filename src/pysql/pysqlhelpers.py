#!/usr/bin/python
# -*- coding: utf-8 -*-

"""This module defines some common useful helper functions
@author: Sébastien Renard (sebastien.renard@digitalfox.org)
@license:GNU GPL V3
"""

# Python imports:
import os
import sys
import traceback
from re import match, sub
import datetime
from cx_Oracle import LOB

# Pysql imports:
from pysqlexception import PysqlException, PysqlActionDenied
from pysqlcolor import BOLD, CYAN, GREEN, GREY, RED, RESET
import pysqlupdate

# Help functions
def addWildCardIfNeeded(aString, wildcard="%"):
    """If aString does not have any wildcard, add one at the begining and one at the end"""
    if not aString.count(wildcard):
        return wildcard+aString+wildcard
    else:
        return aString

def colorDiff(diff):
    """Transforms poorly readable ndiff output into colored diff
    @arg diff: generator returned by difflib.ndiff() function
    @return: list of string diffs with color to highlight diff
    """
    result=[]
    for item in diff:
        if item[0]=="?": # Get diff hint to colorise the previous line
            previous=result[-1] # The line above we want to colorise
            i=0
            coloring=False # flag to start/stop coloring
            newPrevious=[] # the new previous line with color
            for character in item:
                if character=="\n":
                    # End of change. Add end of previous
                    newPrevious.append(previous[i:])
                else:
                    if character in ("-", "^", "+"):
                        if not coloring:
                            newPrevious.append(RED)
                            coloring=True
                    else:
                        if coloring:
                            newPrevious.append(RESET)
                            coloring=False
                    newPrevious.append(previous[i])
                i+=1
            newPrevious.append(RESET) # Always stop color at end of line
            result[-1]="".join(newPrevious) # Create new colorize line
        else:
            result.append(item) # Just store simple line (equal, + or -)
    return result


def convert(value, unit):
    """Converts an number in Bytes into a bigger unit.
       Beware of any data loss"""
    unit=unit.lower()
    if unit=="b":
        return value
    elif unit=="kb":
        return float(value)/1024
    elif unit=="mb":
        return float(value)/1024/1024
    elif unit=="gb":
        return float(value)/1024/1024/1024
    elif unit=="tb":
        return float(value)/1024/1024/1024/1024
    elif unit=="pb":
        return float(value)/1024/1024/1024/1024/1024
    else:
        raise PysqlException(_("Unit not handled: %s") % unit)

def getProg(availables, given, default):
    """Checks if 'given' graphviz program is in the 'availables' list
    Raises an exception if program is not available or return the prog (default if given is 'auto'
    @arg availables: dict of graphviz availables program as return by find_graphivz()
    @arg given: program choose by user
    @arg default: program used if user choose default"""
    if given=="auto":
        given=default
    if not availables.has_key(given):
        raise PysqlActionDenied(given+
                                _(" is not installed. Get it at http://www.graphviz.org/Download.php"))
    else:
        return given

def itemLength(item):
    """Compute length of a result set item"""
    if item is None:
        return 0
    elif isinstance(item, (int, float, long, datetime.datetime)):
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
    result=[]
    endingParenthisis=0
    startsWithParenthisis=True
    lastWordWasOperand=True
    parenthisisBalance=0
    for word in filterClause.split():
        # Keep and remove start & end parenthisis
        while word.startswith("("):
            parenthisisBalance+=1
            startsWithParenthisis=True
            result.append("(")
            word=word[1:]
        while word.endswith(")"):
            parenthisisBalance-=1
            endingParenthisis+=1
            word=word[:-1]
        # Handle boolean operator
        if word.lower() in ("and", "or"):
            if startsWithParenthisis or lastWordWasOperand:
                # Operator at begin of phrase (just after parenthisis)
                # Or two operators following
                raise PysqlException(_("Operator %s was not expected at word %s") % (word.upper(), len(result)+1))
            result.append(word.lower())
            lastWordWasOperand=True
            startsWithParenthisis=False
        # Construct like clause 
        elif len(word)>0 and lastWordWasOperand:
            if word.startswith("!"):
                if len(word)>1 and word[1]=="(":
                    raise PysqlException(_("The ! is not supported before parenthisis"))
                operand="not like"
                word=word[1:]
            else:
                operand="like"
            lastWordWasOperand=False
            startsWithParenthisis=False
            result.append("%s %s '%s'" % (keyword, operand, word))
        elif len(word)>0 and not lastWordWasOperand:
            # Terms of clause must be separted by operators
            raise PysqlException(_("Operator (AND/OR) expected at word %s") % (len(result)+1))
        while endingParenthisis>0:
            endingParenthisis-=1
            result.append(")")
    if parenthisisBalance!=0:
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
    line=sub("\/\*\*\/", " ", line)         # Remove /**/ pattern
    line=sub("\/\*[^+|].*?\*\/", " ", line) # Remove /* ... */ except /*+ ... */
    line=sub("--[^+|].*$", "", line)        # Remove -- ... except --+ ...
    line=sub("--$", "", line)               # Remove -- at the end of line (stupid but allowed)

    if line=="--":
        return "", comment

    # Honors multi line SQL comments but do not shoot Oracle hint!
    # /* comment
    if match(".*/\*[^+].*", line) or match(".*/\*$", line):
        # Remove commented part
        line=sub("/\*[^+|].*", "", line)
        line=sub("/\*$", "", line) # previous regexp does not match */ at end of line
        # Starting multiline comment
        comment=True
    # comment */ (a /* was give before)
    elif match(".*\*\/.*", line) and comment:
        # Remove commented part
        line=sub(".*\*\/", "", line)
        # end for multiline comment
        comment=False
    elif comment:
        line=""
    return (line, comment)

def which(progName):
    """Mimics the Unix which command
    @param progName: program name that will be search through PATH
    @return: full path to program or None if not find in PATH"""
    for directory in os.getenv("PATH").split(os.pathsep):
        fullpath=os.path.join(directory, progName)
        if os.access(fullpath, os.X_OK) and os.path.isfile(fullpath):
            return fullpath
    return None

def warn(message):
    """Just print a formated warning message on screen
    @param message: unicode or str message. Conversion will done with print and default encoding
    """
    print "%s==>Warning:%s %s%s" % (RED, BOLD, message, RESET)

def printStackTrace():
    """Print stack trace with debug information"""
     # Just a hook for a more pleasant error handling
    print "------------------8<-------------------------------------"
    traceback.print_exc()
    print "------------------8<-------------------------------------"
    try:
        pysqlVersion=pysqlupdate.currentVersion()
    except PysqlException:
        pysqlVersion="unknown"
    try:
        import cx_Oracle
        cxVersion=cx_Oracle.version
    except Exception:
        cxVersion="unknown"
    print "Pysql release: %s" % pysqlVersion
    print "cx Oracle release: %s" % cxVersion
    print "Python release: %s" % sys.version.replace("\n", " ")
    print
    print RED+BOLD+"Please, send the text above to pysql@digitalfox.org"+RESET
    print
