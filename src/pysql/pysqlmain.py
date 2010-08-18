#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Pysql is an Oracle client for all those who suffer from sqlplus.

It aims to bring confort and power to user without a heavy graphical application.

Developpers (in order of arrival in the project) :
- Sébastien Renard
- Sébastien Delcros
- <your name here if you want to contribute ! (your firstname must be Sebastien of course)

Requirements:
- Mandatory:
    o python. Pysql has been tested with Python 2.4.x and 2.5.0
    o cx_Oracle : http://www.cxtools.net/default.aspx?nav=cxorlb
- Optionnal:
    o pyreadline for Windows user to have input completion
    o cTypes for windows user to have input completion (already included in Python 2.5)
    o pydot for graphical functions (show datamodel in png for example)
    o pyparser as a dependancy of pydot

Supported plateforms:
- GNU/Linux (developper choice!)
- Windows (some limitations: poor completion and no colors)
- AIX (cx_Oracle is quite painfull to install, but all works correctly)

Pysql should work on many other platform (like Solaris, HPUX, MacOSX, *BSD) but has not been
tested. Feel free to report success to the pysql team.

Installation:
Very simple for the moment, you can put pysql everywhere. Just put the pysql command in your path.

Internationalisation (i18n):
Pysql is available in English (base langage for developpement) and French.
To generate other language messages, use "i18.sh" script in the pysql directory. You'll need
GNU Gettext to achieve this.
Next, to use pysql in French, set the LANG variable to fr (export LANG=fr) « et voilà » !

Documentation:
API documentation can be found in doc/ directory.
User documentation is available in pysql itself. Type « help » to get some help.

Modules overview:
- pysql.py: main module. Just used to setup i18n and fire the shell
- pysqlshell.py: user shell interaction. All pysql « command » are here.
                pysqlshell command handle argument parsing and display.
                Real works is done in pysqlfunction.
- pysqlfunction.py :advanced functions for pysql.
- pysqlconf.py: all configuration stuff (parameters, cache, history, user sql library...)
- pysqloraobject.py: object model for main Oracle objects (table, view, package, index).
                    this is used for functions like desc and edit
- pysqlgraphics.py: all graphical stuff that creates images with graphviz
- pysqlqueries.py: an effort is done to put all SQL queries in this module to have a cleaner code
- pysqlcolor.py: color bank definition
- pysqldb.py: all connection and cursor handling. Also manages background queries
- pysqlexception.py: all pysql defined exceptions

Developpement conventions:
- classes must begin with an uppercase caracter
- variables must begin with a lowercase caracter and user alternate uppercase instead of _
- all lines must be less than 109 characters (ask developpers why)
- all patches must be sent to sebastien@digitalfox.org

@author: Sébastien Renard (sebastien.renard@digitalfox.org)
@author: Sébastien Delcros (Sebastien.Delcros@gmail.com)
@license: GNU GPL V3
"""

# Python imports:
import gettext
import locale
import os
import sys
from os.path import dirname, join, pardir
from optparse import OptionParser

from pysqlcolor import BOLD, CYAN, GREEN, GREY, RED, RESET

# Pysql imports:
from pysqlconf import PysqlConf
from pysqlexception import PysqlException
import pysqlupdate
from pysqlhelpers import printStackTrace, printComponentsVersion

def main():
    """Pysql main function"""
    rc = 0 # Return code

    # Options & args stuf
    (options, argv) = parseOptions()

    # i18n stuff
    if os.name == "nt":
        # Windows stuff is never like everybody...
        i18nPath = join(dirname(sys.argv[0]), "share", "locale")
    else:
        # Unix std path
        i18nPath = join(dirname(sys.argv[0]), pardir, "share", "locale")
    # Loads message catalog
    gettext.install("pysql", i18nPath, unicode=1)

    # Loads config (first time)
    conf = PysqlConf.getConfig()

    # Sets the locale
    setLocale(conf)

    try:
        if options.update:
            try:
                pysqlupdate.checkForUpdate(options.proxyHost, options.proxyUser, options.proxyPassword)
            except KeyboardInterrupt:
                print _("Aborting update")
        elif options.version:
            printComponentsVersion()
        else:
            try:
                import cx_Oracle
            except ImportError:
                # Untranslatable error message (i18n still not initialized at this step)
                print RED + BOLD + "cx_Oracle module cannot be loaded." + RESET
                print
                print "Please, ensure you correctly install it from: " + CYAN + "http://cx-oracle.sf.net" + RESET
                print "And that have the according Oracle client installation."
                print "Get it from the Oracle site : http://www.oracle.com"
                print
                print "(press enter key to exit)"
                sys.stdin.readline()
                sys.exit(1)
            # Now we can import PysqlShell (and subsequent modules that depends on cx_Oracle)
            from pysqlshell import PysqlShell
            # Default is to launch pysql in standard mode (local client) 
            shell = PysqlShell(silent=options.silent, argv=argv)
            if options.oneTryLogin and shell.db == None:
                rc = 1
            else:
                shell.loop()
                rc = shell.rc
        # Bye
        if os.name == "nt" and not options.version:
            # Don't exit too fast for windows users, else they don't see error sum up
            print _("(press any key to exit)")
            sys.stdin.readline()
    except StandardError, e:
        # Just a hook for a more pleasant error handling
        print "\n==> Unrecoverable error during initialisation. Exiting <=="
        printStackTrace()
        print _("(press enter key to exit)")
        sys.stdin.readline()
    except PysqlException, e:
        print "*** " + _("Pysql error") + " ***"
        print "\t%s" % e

    # Bye!
    sys.exit(rc)

def setLocale(conf):
    """Sets the right encoding"""
    try:
        codec = locale.getpreferredencoding()
    except:
        # default to latin-1
        codec = "latin-1"
    if codec is None:
        codec = "latin-1"
    # Tests if codec exists
    try:
        str().encode(codec)
    except LookupError:
        codec = "latin-1"

    # Stores codec in config
    conf.setCodec(codec)

    # Sets default encoding for stdout
    reload(sys)
    sys.setdefaultencoding(codec)

def parseOptions():
    """Parses pysql command argument using optparse python module"""
    parser = OptionParser()

    # Version
    parser.add_option("-v", "--version", dest="version", action="store_true",
              help="prints PySQL version")

    # Silent mode
    parser.add_option("-S", "--Silent", dest="silent", action="store_true",
              help="sets silent mode which suppresses the dispay of banner, prompts and echoing of commands")

    # Login
    parser.add_option("-L", "--Login", dest="oneTryLogin", action="store_true",
              help="exits if login attempt failed, instead of starting not connected")

    # Update mode
    parser.add_option("-u", "--update", dest="update", action="store_true",
              help="checks if PySQL update are available")
    parser.add_option("-H", "--proxyHost", dest="proxyHost", type="string", default=None,
              help="proxy hostname for PySQL update. \t\tExample: 'http://my-proxy.mydomain:8080'")
    parser.add_option("-U", "--proxyUser", dest="proxyUser", type="string", default="",
              help="proxy username if authentication is required")
    parser.add_option("-P", "--proxyPassword", dest="proxyPassword", type="string", default="",
              help="proxy password if authentication is required")

    return parser.parse_args()

###### Starts Pysql ########
if __name__ == "__main__":
    main()
