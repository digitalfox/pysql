#!/usr/bin/python
# -*- coding: utf-8 -*-

"""User interaction with pysql
@author: Sébastien Renard (sebastien.renard@digitalfox.org)
@author: Sébastien Delcros (Sebastien.Delcros@gmail.com)
@license:GNU GPL V3
"""

# Python imports:
import cmd
import sys
import os
import readline
from re import findall, match, sub
from os.path import expandvars
from time import sleep, time
from getpass import getpass
import csv

# Pysql imports:
from pysqldb import PysqlDb, BgQuery
import pysqlfunctions
import pysqlgraphics
from pysqlexception import PysqlException, PysqlNotImplemented, PysqlOptionParserNormalExitException
from pysqlconf import PysqlConf
from pysqlcolor import BOLD, CYAN, GREEN, GREY, RED, RESET
from pysqlhelpers import itemLength, removeComment, printStackTrace, setTitle, getTitle
from pysqloptionparser import PysqlOptionParser

class PysqlShell(cmd.Cmd):
    """Main class that handle user interaction"""

    def __init__(self, completekey='tab', stdin=None, stdout=None, argv=[]):
        """Shell initialisation"""

        # Instance attributs
        self.db=None                # Db connection object
        self.fetching=False         # Indicate if a request is running
        self.multilineCmd=False     # Indicate if the user is in a multiline command
        self.plBloc=False           # Indicate if the user is in a PL/SQL bloc
        self.comment=False          # Indicate if the user is in an SQL multiline comment
        self.cmdBuffer=[]           # Command buffer for multiline command (list of line)
        self.lastStatement=""       # Last statement executed
        self.tnsnamesAvailable=None # possible to read tnsnames.ora for completion ?
        self.conf=None              # Handle to pysql configuration instance
        self.cmds=[]                # List of defined cmds
        self.bgQueries=[]           # List of bg queries threads
        self.exceptions=[]          # List of PysqlException encountered
        self.useCompletion=True     # Indicate if we should use completion with "tab"
        self.showBanner=True        # Indicate if intro banner should be displayed
        self.trace={}               # Store session trace statistics between two call to trace command
        self.rc=0                   # Shell exit code
        self.oldTermName=""         # Old terminal name
        self.notConnectedPrompt=RED+_("(not connected) ")+RESET

        # Reads conf
        self.conf=PysqlConf.getConfig()

        # Are we in tty (user interaction) or not (script, pipe...) ?
        # If not, doesn't use completion in script
        if not sys.stdin.isatty():
            self.useCompletion=False

        # Calls father constructor
        cmd.Cmd.__init__(self, "tab", stdin, stdout)

        # Keep old term name
        self.oldTermName=getTitle()

        # If connectString was given as argument, connects to Oracle
        try:
            self.__connect(argv[0])
        except IndexError:
            # No argv given. Starts not connected
            self.__setPrompt()
        except PysqlException, e:
            # Connection failed, start not connected and warn user
            print RED+BOLD+_("\nConnection failed:\n\t %s") % e + RESET
            self.exceptions.append(e)
            self.db=None
            self.__setPrompt()
        except KeyboardInterrupt:
            print RED+BOLD+_("Break !")+RESET
            #TODO: validates this case (direct call of __exit() is not good)
            self.__exit()

    def preloop(self):
        """Prepares shell interactive loop"""
        # Builds the list of commands
        self.cmds=[i[3:] for i in self.get_names() if i.startswith("do_")]
        self.cmds.remove("explain") # explain command use multine
        self.cmds.remove("csv") # so does csv
        if self.showBanner:
            banner=_("\nWelcome to pysql shell\n")
            banner+=_("Type 'help' for some help.\nUse Tab for completion\n")
        else:
            banner=""
        print banner

    def loop(self):
        """Starts shell interactive loop"""
        try:
            self.cmdloop()
        except KeyboardInterrupt:
            # Does not work when a connection is made to Oracle
            # Question asked to cx_Oracle developer. Waiting for answer.
            print RED+BOLD+_("Break !")+RESET
            self.showBanner=False
            self.loop()

    def postloop(self):
        """End of command loop"""
        # Restore original terminal title
        setTitle(self.oldTermName, self.conf.getCodec())

    def emptyline(self):
        """Fetches next result if a request is running
        or do nothning"""
        if self.fetching:
            try:
                self.__fetchNext()
            except PysqlException, e:
                self.fetching=False
                raise PysqlException(e)

    def onecmd(self, line):
        """This method is subclassed just to be
        able to encapsulate it with a try/except bloc"""
        try:
            return cmd.Cmd.onecmd(self, line)
        except PysqlOptionParserNormalExitException:
            # Do nothing, we are just catching parser exit function when help is called
            pass
        except PysqlException, e:
            print RED+BOLD+_("*** Pysql error ***\n\t%s") % e + RESET
            self.exceptions.append(e)
            if e.oraCode=="ORA-03114": # Not connected to Oracle
                self.db=None
        except KeyboardInterrupt:
            print RED+BOLD+_("Break !")+RESET
        except StandardError, e:
            # Just a hook for a more pleasant error handling
            print RED+BOLD+"\n==> Unhandled error. Sorry <=="+RESET
            printStackTrace()

    def precmd(self, line):
        """Hook executed just before any command execution.
        This is used to parse command and dispatch it to Oracle or internal pysql functions"""

        # Decode line from user encoding to unicode
        line=line.decode(self.conf.getCodec())

        if self.conf.get("echo")=="yes":
            # Echo line to stdout
            print line

        line, self.comment=removeComment(line, self.comment)

        # Removes leading and trailing whitespace
        line=line.strip()

        # Does nothing for blank line or EOF
        if len(line)==0 or line=="EOF":
            return line

        # The @ is a shortcut to the script command
        if line[0]=="@":
            return "script "+line[1:]

        firstWord=line.split()[0]

        # Substitute alias with real function name
        if self.aliases.has_key(firstWord):
            line=line.replace(firstWord, self.aliases[firstWord], 1)
            firstWord=self.aliases[firstWord]

        # Pysql command are single line
        if (firstWord in self.cmds or line[0]=="!") and not self.multilineCmd:
            # ; is not needed but we remove it if exists
            if firstWord!="set":
                # Don't strip for set command else we cannot use a parameter with a ; at the end !
                line=line.rstrip(";")
            return line

        if firstWord.lower() in ("declare", "begin"):
            # PL/SQL Bloc detected
            self.plBloc=True
        elif firstWord=="/" and not self.plBloc and not self.multilineCmd:
            # Repeats the last statement
            if self.lastStatement:
                return self.lastStatement.rstrip(";")
            else:
                return ""

        if (line[-1] in [";", "&", "/"] and not self.plBloc) or (line[-1]=="/" and self.plBloc):
            # End of command line detected
            # Removes trailing / and ;
            line=line.rstrip(";")
            line=line.rstrip("/")
            self.cmdBuffer.append(line)
            line=" ".join(self.cmdBuffer)
            self.cmdBuffer=[]
            self.__setPrompt() # back to std prompt
            if self.multilineCmd:
                # Puts the whole command line into history
                try:
                    length=readline.get_current_history_length()
                    if length>1:
                        readline.replace_history_item(length-1, line) # put the complete cmd in history
                except AttributeError:
                    # Windows readline does not have those advanced functions... Sad world
                    pass
            self.multilineCmd=False
            self.plBloc=False
        else:
            # Checks sql given is not too dumb (check only the begining !)
            if not self.multilineCmd:
                result=match("(.+?)\s.+", line)
                if result:
                    firstWord=result.group(1)
                else:
                    firstWord=line
            if not self.multilineCmd \
               and firstWord.lower() not in ("select", "insert", "update", "delete",
                                             "alter", "truncate", "drop", "begin",
                                             "declare", "comment", "create", "grant",
                                             "revoke", "analyze", "explain", "csv"):
                print RED+BOLD+_("Unknown command or sql order. Type help for help")+RESET
            else:
                # Bufferise the command and wait for the rest
                self.multilineCmd=True
                self.cmdBuffer.append(line)
                self.fetching=False # Cancel previous fetching if any
                self.__setPrompt(blank=True) # blank the prompt (for easy cut&paste !)
                try:
                    length=readline.get_current_history_length()
                    if length>1:
                        # Removes partial line from history
                        readline.remove_history_item(length-1)
                except AttributeError:
                    # Windows readline does not have those advanced functions... Sad world
                    pass
            # In both case, do nothing, so the line is set to blank
            line=""
        return line

    def postcmd(self, stop, line):
        """Hook executed just after command processing.
        Used to notify running and finished background queries
        @return: stop flag to end loop"""
        if self.multilineCmd:
            self.__setPrompt(blank=True)
        else:
            queries=[i for i in self.bgQueries if not i.isAlive()]
            if len(queries)!=0:
                self.__setPrompt(finishedQuery=True)
            else:
                self.__setPrompt()
        return stop

    def default(self, arg):
        """Default method if no command is recognized.
        We assume it is a pure SQL request"""
        if arg=="EOF":
            return self.__exit()
        else:
            self.__executeSQL(arg)

    def do_help(self, arg):
        """
        Overload do_help to show help from the command parser if it exists:
        if there is a parser_foo() method, assume this method returns a
        PysqlOptionParser for the do_foo() method and show the help of the
        parser, instead of standard help (do_foo() docstring or help_foo())
        """
        if self.aliases.has_key(arg):
            arg=self.aliases[arg]
        if hasattr(self, "parser_" + arg):
            parserMethod = getattr(self, "parser_" + arg)
            parserMethod().print_help(sys.stderr)
        else:
            cmd.Cmd.do_help(self, arg)

    def completenames(self, text, *ignored):
        """Complete commands names. Same as Cmd.cmd one but with support
        for command aliases"""
        dotext = 'do_'+text
        names = [a[3:] for a in self.get_names() if a.startswith(dotext)]
        names.extend([a for a in self.aliases.keys() if a.startswith(text)])
        return names

    def completedefault(self, text, line, begidx, endidx):
        """pysql specific completion with self.completeList"""
        if not self.useCompletion:
            return
        # Keyword detection not very smart... but work for simple case
        lastKeyWord=line[:begidx].split()[-1].lower()
        if   lastKeyWord in ["select", "where", "by",
                     "sum(", "abs(", "round(", "upper(", "lower(", "set"]:
            themes=["columns"]
        elif lastKeyWord in ["update"]:
            themes=["table"]
        elif lastKeyWord in ["from", "into"]:
            themes=["table", "view", "synonym"]
        elif lastKeyWord=="index":
            themes=["index"]
        elif lastKeyWord=="table":
            themes=["table"]
        elif lastKeyWord=="sequence":
            themes=["sequence"]
        elif lastKeyWord=="directory":
            themes=["directory"]
        elif lastKeyWord=="index":
            themes=["trigger"]
        elif lastKeyWord=="view":
            themes=["view"]
        elif lastKeyWord=="user":
            themes=["user"]
        else:
            themes=["table", "view", "synonym", "columns",
                "directory", "sequence", "user"]
        # Separates text from his prefix
        if text.count(".")==1:
            prefix, text=text.split(".")
            prefix+="." # Doesn't forget the dot for the prefix
        else:
            prefix=""
        return self.__getCompletionItems(text, themes, prefix)

    def complete_connect(self, text, line, begidx, endidx):
        """Completion of SID for connect method"""
        if not self.useCompletion:
            return
        # Completes only on SID (after the @)
        if line.count("@"):
            sid=line.split("@")[-1]
        else:
            # No @, cannot complete.
            return []

        if self.tnsnamesAvailable is None:
            # First try to open tnsnames.ora
            try:
                tnsnames=file(expandvars("$ORACLE_HOME/network/admin/tnsnames.ora")).readlines()
                self.conf.completeLists["SID"]=sum([findall("^(\w+)\s*=",line) for line in tnsnames],[])
                self.tnsnamesAvailable=True
            except Exception, e:
                # Do not raise a PysqlException (useless)
                print RED+BOLD+_("Cannot open tnsnames.ora file (%s)") % e + RESET
                self.tnsnamesAvailable=False
        if self.tnsnamesAvailable:
            return self.__getCompletionItems(sid, ["SID"])
        else:
            return []

    def complete_desc(self, text, line, begidx, endidx):
        """Completion for command desc"""
        if not self.useCompletion:
            return
        return self.__getCompletionItems(text, ["table", "view", "index",
                            "synonym", "sequence",
                            "tablespace", "datafile"
                            "directory"])

    def complete_edit(self, text, line, begidx, endidx):
        """Completion for command edit"""
        if not self.useCompletion:
            return
        return self.__getCompletionItems(text, ["view", "package"])

    def complete_get(self, text, line, begidx, endidx):
        """Completion for command get"""
        if not self.useCompletion:
            return
        return self.__getCompletionItems(text, ["parameters"])

    def complete_set(self, text, line, begidx, endidx):
        """Completion for command set"""
        if not self.useCompletion:
            return
        return self.__getCompletionItems(text, ["parameters"])

    def complete_library(self, text, line, begidx, endidx):
        """Completion for library command"""
        return [k for k  in self.conf.sqlLibrary.keys() if k.startswith(text)]

    # Command line definitions
    # Connection stuff
    def do_connect(self, arg):
        """Connect to instance"""
        self.__checkArg(arg, ">=1")
        arg=arg.split()
        try:
            self.__disconnect()
        except PysqlException, e:
            print RED+BOLD+_("Error while closing previous connection:\n\t %s") % e + RESET
            self.exceptions.append(e)
            self.db=None
        if len(arg)==1:
            mode=""
        elif arg[1].lower()=="sysdba":
            mode="sysdba"
        elif arg[1].lower()=="sysoper":
            mode="sysoper"
        else:
            mode=""
            print RED+BOLD+_("Invalid Oracle mode: %s (ignored)") % arg[1] + RESET
        self.__connect(arg[0], mode)

    def do_disconnect(self, arg):
        """Disconnect from instance"""
        try:
            self.__disconnect()
        except PysqlException, e:
            self.db=None
            # Proxy the exception for standard handling
            raise PysqlException(e)

    # Completion, history and sql library
    def do_showCompletion(self, arg):
        """Shows completion list"""
        for theme in self.conf.completeLists.keys():
            print GREEN+("***** %s *****" % theme)+RESET
            self.__displayCol(self.conf.completeLists[theme])
            print

    def do_history(self, arg):
        """Display shell history"""
        self.__checkArg(arg, "<=1")
        #TODO: move depth to pysqlConfig
        #BUG: if history is short stupid things are printed !
        depth=20 # Number of history item to be displayed
        try:
            length=readline.get_current_history_length() # Length of current history in readline buffer
        except AttributeError:
            message=_("History not available on Windows platform (readline limitation)")
            raise PysqlException(message)
        arg=arg.split()
        if len(arg)==0:
            # Display history
            for i in xrange(depth):
                position=length-depth+i
                # Data is already encoded
                print "%d: %s " % (position, readline.get_history_item(position))
        elif len(arg)==1:
            # Executes the nth command
            try:
                position=int(arg[0])
            except ValueError:
                raise PysqlException(_("Argument must be an integer"))

            if position>length:
                raise PysqlException(_("This is the future ! Cannot execute. Sorry"))
            elif position<=0:
                raise PysqlException(_("Argument should be stricly positive"))
            else:
                command=readline.get_history_item(position)
                command=self.precmd(command)
                print command
                self.onecmd(command)
        else:
            raise PysqlException(_("See help history for usage"))

    def do_library(self, arg):
        """Manage user sql request library"""
        nArgs=len(arg.split())
        if nArgs==0:
            # Shows all sql library
            self.__displayTab(self.conf.sqlLibrary.items(), ("Name", "SQL request"))
        elif nArgs==1:
            # Recalls a request
            if self.conf.sqlLibrary.has_key(arg):
                readline.add_history(self.conf.sqlLibrary[arg])
                print GREEN+ \
                            _("SQL request was loaded in your history. Use up arrow to get it now") \
                            +RESET
            else:
                msg=_("Request %s does not exist. Type 'lib' without argument to see all request") % arg
                raise PysqlException(msg)
        elif nArgs>1:
            # First argument is name and second argument can be sql or keyword remove
            name=arg.split()[0]
            text=" ".join(arg.split()[1:])
            if text=="remove":
                if self.conf.sqlLibrary.has_key(name):
                    del self.conf.sqlLibrary[name]
                    print GREEN+_("Request has been removed")+RESET
                else:
                    msg=_("Request %s does not exist. Type 'lib' without argument to see all request") % name
                    raise PysqlException(msg)
            else:
                # Add request
                self.conf.sqlLibrary[name]=text
                print GREEN+_("Request has been saved")+RESET

    # background queries
    def do_bg(self, arg):
        """Manage background queries"""
        arg=arg.split()
        if len(arg)==0:
            # Shows background queries
            result=[(i.getName(), i.query, not i.isAlive(), i.error) for i in self.bgQueries]
            self.__displayTab(result, ["#", "SQL Request", "Finished?", "Error"])
        elif len(arg)==1:
            # Finds the thread
            bgQuery=[i for i in self.bgQueries if i.getName()==arg[0]]
            if len(bgQuery)==1:
                bgQuery=bgQuery[0]
                # Waits for query ending
                bgQuery.join()
                # Gets this query in foreground
                if bgQuery.query.upper().split()[0].startswith("SELECT"):
                    self.db=bgQuery.db
                    self.__toScreen(bgQuery.result, bgQuery.moreRows)
                else:
                    print GREEN+ _("Statement executed")+RESET
                # Removes bg query from list
                self.bgQueries.remove(bgQuery)
            else:
                raise PysqlException(_("Unknown background query. Use bg without arg to see all queries"))
        else:
            raise PysqlException(_("See help bg for description"))

    # Transactions stuff
    def do_commit(self, arg):
        """Commit pending transaction"""
        self.__checkConnection()
        self.db.commit()
        print GREEN+_("Commit completed")+RESET

    def do_rollback(self, arg):
        """Rollback pending transaction"""
        self.__checkConnection()
        self.db.rollback()
        print GREEN+_("Rollback completed")+RESET

    # High level functions
    def do_count(self, arg):
        """Count segment lines"""
        self.__checkConnection()
        self.__checkArg(arg, "==1")
        result=pysqlfunctions.count(self.db, arg)
        print result

    def do_compare(self, arg):
        """Compare schema or object structure and data"""
        self.__checkArg(arg, ">=2")
        schemaNames=[] # Password striped connection string to schema
        tableNames=[]
        schemas=[]     # Complete connect string to schema
        withData=False # Compare only structure (false) or data ?

        arg=arg.split()

        if arg[0]=="data":
            withData=True
            arg.pop(0)
        elif arg[0]=="structure":
            withData=False
            arg.pop(0)

        for item in arg:
            result=match("(.+?)/(.+?)@(\w+):?(.*)", item)
            if result:
                # Schema given
                schemaNames.append(result.group(1)+"@"+result.group(3))
                if result.group(4):
                    # Table name also given
                    tableNames.append(result.group(4))
                    schemas.append(item.split(":")[0])
                else:
                    schemas.append(item)
            else:
                # Only tablename given
                tableNames.append(item)

        if not schemas:
            # We assume schema is current schema
            self.__checkConnection()
            schemas=["A", "B"]
            # We create two new connexion to avoid cursor clash
            dbList={ schemas[0] : PysqlDb(self.db.getConnectString()),
                     schemas[1] : PysqlDb(self.db.getConnectString()) }
        else:
            # Connection will be created later by compareTables(...)
            dbList=None

        if tableNames:
            # We are just comparing two tables
            if len(tableNames)!=2:
                raise PysqlException(_("Cannot compare a table and a schema !"))
            result=pysqlfunctions.compareTables(schemas[0], schemas[1],
                                                tableNames[0], tableNames[1],
                                                dbList, data=withData)
            if result:
                print CYAN+ \
                            """Table %s (marked with "-") differ from table %s (marked with "+")""" \
                            % (tableNames[0], tableNames[1])+ RESET
                print "\n".join(result)
            else:
                print _("Tables are identical")
        else:
            # We have to compare the whole schema
            result=pysqlfunctions.compare(schemas[0], schemas[1])

            print GREEN+_("**** Tables found in %s but not in %s ****") \
                        % (schemaNames[0], schemaNames[1])+RESET
            print ", ".join(result[0])
            print

            print GREEN+_("**** Tables found in %s but not in %s ****") \
                        % (schemaNames[1], schemaNames[0])+RESET
            print ", ".join(result[1])
            print

            print GREEN+_("**** Tables identical in both schema ****")+RESET
            print ", ".join([i[0] for i in result[2].items() if not i[1]])
            print

            print GREEN+_("**** Tables not identical in both schema ****")+RESET
            for tableName, tableDiff in result[2].items():
                if tableDiff:
                    print CYAN+_("""Table %s differ from schema %s""")  \
                            % (tableName, schemaNames[0]),
                    print _("""(marked with "-") and schema %s (marked with "+")""") \
                            % schemaNames[1] +RESET
                    print "\n".join(tableDiff)
                    print

    def parser_describe(self):
        parser=PysqlOptionParser()
        parser.set_usage("desc[ribe] [options] <object name>")
        parser.set_description("Describes any Oracle object")
        parser.add_option("-s", "--sort", dest="sort",
                          default=False, action="store_true",
                          help="Sort column alphabetically instead of Oracle order")
        return parser

    def do_describe(self, arg):
        """Emulates the sqlplus desc function"""
        parser = self.parser_describe()
        options, args = parser.parse_args(arg)
        self.__checkConnection()
        self.__checkArg(args, "==1")
        # Gives method pointer to desc function to allow it to update completelist
        (header, result)=pysqlfunctions.desc(self.db, args[0],
                                             completeMethod=self.__addToCompleteList,
                                             sort=options.sort)
        self.__displayTab(result, header)

    def parser_datamodel(self):
        parser=PysqlOptionParser()
        parser.set_usage("datamodel [options] [filters on table name]]")
        parser.set_description(
            "Extracts the datamodel of a user filtered on selected table pattern. "
            "The generation of the output is powered by Graphviz (http://www.graphviz.org)"
            )
        if self.db:
            defaultUser=self.db.getUsername()
        else:
            defaultUser=""
        parser.add_option("-c", "--columns", dest="columns",
                          default=False, action="store_true",
                          help="Also draw table's columns")

        parser.add_option("-u", "--user", dest="user",
                          default=defaultUser,
                          help="User owner of tables (schema)")
        return parser

    def do_datamodel(self, arg):
        """Exports a datamodel as a picture"""
        self.__checkConnection()
        parser = self.parser_datamodel()
        options, args = parser.parse_args(arg)
        pysqlgraphics.datamodel(self.db, options.user.upper(),
                                tableFilter=" ".join(args),
                                withColumns=options.columns)

    def parser_dependencies(self):
        parser=PysqlOptionParser()
        parser.set_usage("dep[endencies] [options] <object name>")
        parser.set_description(
            "Displays object dependencies as a picture. "
            "The generation of the output is powered by Graphviz (http://www.graphviz.org)"
            )
        directions=("onto", "from", "both")
        parser.add_option("-d", "--direction", dest="direction",
                          default="both", type="choice",
                          metavar="<direction>", choices=directions,
                          help="Direction of dependency tracking: %s" % ", ".join(directions))
        parser.add_option("-r", "--recursion", dest="maxDepth",
                          default=self.conf.get("graph_depmaxdepth"), type="int",
                          help="Maximum level of recursion")
        parser.add_option("-n", "--nodes", dest="maxNodes",
                          default=self.conf.get("graph_depmaxnodes"), type="int",
                          help="Maximum number of nodes on graph")
        return parser

    def do_dependencies(self, arg):
        """Exports object dependencies as a picture"""
        self.__checkConnection()
        parser = self.parser_dependencies()
        options, args = parser.parse_args(arg)
        self.__checkArg(args, "=1")
        pysqlgraphics.dependencies(self.db, args[0],
                                   options.direction,
                                   options.maxDepth,
                                   options.maxNodes)

    def parser_diskusage(self):
        parser=PysqlOptionParser()
        parser.set_usage("diskusage (or du) [options] <schema name>")
        parser.set_description(
            "Extracts the physical storage of a user as a picture based on Oracle statistics. "
            "The generation of the output is powered by Graphviz (http://www.graphviz.org)"
            )
        parser.add_option("-i", "--index", dest="index",
                  default=False, action="store_true",
                  help="Also draw index segment")

        return parser

    def do_diskusage(self, arg):
        """Exports disk usage as a picture"""
        self.__checkConnection()
        parser = self.parser_diskusage()
        options, args = parser.parse_args(arg)
        try:
            user=args[0]
        except IndexError:
            user=self.db.getUsername()
        pysqlgraphics.diskusage(self.db, user.upper(), options.index)

    def do_ddl(self, arg):
        """Prints Oracle object DDL"""
        self.__checkConnection()
        self.__checkArg(arg, "==1")
        result=pysqlfunctions.ddl(self.db, arg)
        if result is None:
            print CYAN+_("(no result)")+RESET
        else:
            print result.rstrip(" ").rstrip("\n")+";"

    def do_edit(self, arg):
        """Edits properties of an Orale object or last SQL statement"""
        self.__checkConnection()
        nArgs=len(arg.split())
        if nArgs==0:
            # Edits last statement
            result=pysqlfunctions.editor(self.lastStatement + ";")
            if result:
                result=result.rstrip("\n")
                readline.add_history(result)
                self.lastStatement=result
        elif nArgs==1:
            # Edits Oracle object
            if pysqlfunctions.edit(self.db, arg):
                print GREEN+ _("(Update successful)")+RESET
            else:
                print CYAN+_("(no result)")+RESET
        else:
            raise PysqlException(_("Incorrect arguments. See help edit"))

    def do_execute(self, arg):
        """ Emulates sqlplus execute"""
        self.__checkConnection()
        self.__checkArg(arg, ">=1")
        line="begin\n" + arg + ";\nend;\n"
        self.__executeSQL(line)

    def do_explain(self, arg):
        """Explain SQL exec plan"""
        self.__checkConnection()
        self.__checkArg(arg, ">1")
        importantWords=["TABLE ACCESS FULL", "FULL SCAN"]
        result=pysqlfunctions.explain(self.db, arg)
        for line in result:
            line=line[0]
            for word in importantWords:
                line=sub("(.*)("+word+")(.*)", r"\1"+RED+r"\2"+RESET+r"\3", line)
            print line

    def parser_session(self):
        parser=PysqlOptionParser()
        parser.set_usage("session [options] <session id>")
        parser.set_description("Display Oracle sessions. "
                               "If a session id is provided, display detailed session informations, "
                               "else display all session summary")
        parser.add_option("-a", "--all", dest="all",
                          default=False, action="store_true",
                          help="Display all foreground sessions, both active and inactive")
        return parser


    def do_session(self, arg):
        """Display Oracle session"""
        self.__checkConnection()
        parser = self.parser_session()
        options, args = parser.parse_args(arg)
        if options.all and args:
            print CYAN+"Note: the all (-a / --all) option is useless when display one session"+RESET
        if not args:
            # Lists all session
            result=pysqlfunctions.sessions(self.db, all=options.all)
            self.__displayTab(result, self.db.getDescription())
        else:
            sessionId=args[0]
            # Displays details about one session
            print CYAN+_("***** Input/Output statistics *****")+RESET
            result=pysqlfunctions.sessionStat(self.db, sessionId, stat="ios")
            self.__displayTab(result, self.db.getDescription())
            print CYAN+_("***** Wait events***** ")+RESET
            result=pysqlfunctions.sessionStat(self.db, sessionId, stat="waitEvents")
            self.__displayTab(result, self.db.getDescription())
            print CYAN+_("***** Current statement *****")+RESET
            result=pysqlfunctions.sessionStat(self.db, sessionId, stat="currentStatement")
            if result and result[0][0]:
                result="".join([i[0] for i in result]) # Merge all in one string
                result=sub("\s+", " ", result) # Strip extra spaces
                print result
                try:
                    if not result.upper().startswith("ALTER"):
                        self.do_explain(result)
                except PysqlException, e:
                    # Should be a privilege exception. Delay error at this end
                    print _("Cannot explain plan (%s)") % e
            else:
                print _("No statement")
            print CYAN+_("***** Open cursors *****")+RESET
            result=pysqlfunctions.sessionStat(self.db, sessionId, stat="openCursors")
            self.__displayTab(result, self.db.getDescription())
            print CYAN+_("***** Locks *****")+RESET
            result=pysqlfunctions.sessionStat(self.db, sessionId, stat="locks")
            self.__displayTab(result, self.db.getDescription())

    def do_kill(self, arg):
        """Kill sessions"""
        self.__checkConnection()
        self.__checkArg(arg, "==2")
        pysqlfunctions.killSession(self.db, arg.replace(" ", ","))
        print GREEN+_("Kill has been sent to the session")+RESET

    def do_lock(self, arg):
        """Display instance lock"""
        self.__checkConnection()
        self.__checkArg(arg, "==0")
        (header, result)=pysqlfunctions.lock(self.db)
        self.__addToCompleteList([i[0] for i in result], "columns") # buggy !
        self.__displayTab(result, header)

    def do_trace(self, sid):
        """Trace a session"""
        self.__checkConnection()
        self.__checkArg(sid, "==1")
        try:
            if self.trace.has_key(sid):
                # Ends trace capture and display result
                ios=list(pysqlfunctions.sessionStat(self.db, sid, "ios")[0])
                iosHeader=self.db.getDescription()
                waits=list(pysqlfunctions.sessionStat(self.db, sid, "waitEvents")[0])
                waitsHeader=self.db.getDescription()
                def conv(item):
                    """Sub function to convert str to int and NULL to 0"""
                    if item is None:
                        return 0
                    else:
                        try:
                            return int(item)
                        except ValueError:
                            return 0
                ios=[conv(i) for i in ios]
                waits=[conv(i) for i in waits]
                self.trace[sid][0]=[conv(i) for i in self.trace[sid][0]]
                self.trace[sid][1]=[conv(i) for i in self.trace[sid][1]]
                resultIos=[]
                resultWaits=[]
                for i in xrange(len(ios)):
                    resultIos.append(ios[i]-self.trace[sid][0][i])
                    resultWaits.append(waits[i]-self.trace[sid][1][i])
                print CYAN+_("***** Input/Output delta for session %s *****") % sid +RESET
                self.__displayTab([resultIos], iosHeader)
                print CYAN+_("***** Wait events delta for session %s ***** ") % sid +RESET
                self.__displayTab([resultWaits], waitsHeader)
                # Removes trace point for this session
                del self.trace[sid]
            else:
                # Starts trace capture
                print CYAN+_("Starting trace capture for session %s") % sid + RESET
                print CYAN+_("""Type "trace %s" again to stop trace on this sesssion""") % sid + RESET
                ios=list(pysqlfunctions.sessionStat(self.db, sid, "ios")[0])
                waits=list(pysqlfunctions.sessionStat(self.db, sid, "waitEvents")[0])
                # Stores to trace dict to compute diff on next trace call
                self.trace[sid]=[ios, waits]
        except IndexError:
            msg=_("Session %s does not exist or you are not allowed to see session details") % sid
            raise PysqlException(msg)

    def do_pkgtree(self, arg):
        """Display PL/SQL package call tree"""
        self.__checkConnection()
        self.__checkArg(arg, "==1")
        #raise PysqlNotImplemented()
        pysqlgraphics.pkgTree(self.db, arg)

    # Oracle object searching (in alphabectic order)
    def do_datafile(self, arg):
        """Display datafile"""
        self.__searchObjet("datafile", arg)

    def do_directory(self, arg):
        """Display directories"""
        self.__searchObjet("directory", arg)

    def do_function(self, arg):
        """Display functions"""
        self.__searchObjet("function", arg)

    def do_index(self, arg):
        """Display indexes"""
        self.__searchObjet("index", arg)

    def do_package(self, arg):
        """Display PL/SQL packages"""
        self.__searchObjet("package", arg)

    def do_procedure(self, arg):
        """Display PL/SQL procedures"""
        self.__searchObjet("procedure", arg)

    def do_segment(self, arg):
        """Display segments (tables, index)"""
        print CYAN+_("***** Tables *****")+RESET
        self.__searchObjet("table", arg)
        print CYAN+_("\n**** Indexes *****")+RESET
        self.__searchObjet("index", arg)

    def do_sequence(self, arg):
        """Display sequences"""
        self.__searchObjet("sequence", arg)

    def do_table(self, arg):
        """Display tables"""
        self.__searchObjet("table", arg)

    def do_trigger(self, arg):
        """Display triggers"""
        self.__searchObjet("trigger", arg)

    def do_view(self, arg):
        """Display view"""
        self.__searchObjet("view", arg)

    def do_tablespace(self, arg):
        """Display tablespaces"""
        self.__searchObjet("tablespace", arg)

    def do_user(self, arg):
        """Display users (aka schema)"""
        self.__searchObjet("user", arg)

    # Cursor manipulation
    def do_last(self, arg):
        """Display last lines of query set"""
        self.__checkConnection()
        self.__checkArg(arg, "<=1")
        try:
            nbLines=int(arg)
            if nbLines<self.conf.get("fetchSize"):
                # Don't fetch too small (perf purpose)
                fetchSize=self.conf.get("fetchSize")
            else:
                fetchSize=nbLines
        except (ValueError, TypeError):
            nbLines=self.conf.get("fetchSize")
            fetchSize=nbLines

        moreRows=True
        result=[]
        while moreRows:
            previousResult=result
            (result, moreRows)=self.db.fetchNext(fetchSize)
        previousResult.extend(result)
        result=previousResult[-nbLines:]
        self.__displayTab(result, self.db.getDescription())

    def do_next(self, arg):
        """Display next lines of query set"""
        self.__checkConnection()
        self.__checkArg(arg, "<=1")
        try:
            nbLines=int(arg)
        except (ValueError, TypeError):
            nbLines=0
        self.__fetchNext(nbLines)

    # Parameters handling
    def do_get(self, arg):
        """Get pysql parameter"""
        if arg in ("all", ""):
            result=self.conf.getAll()
            # Converts all to str to avoid strange alignement
            for i in xrange(len(result)):
                result[i]=[str(result[i][j]) for j in xrange(len(result[i]))]
            self.__addToCompleteList([i[0] for i in result], "parameters")
            self.__displayTab(result,
                ["Parameter", "User defined value", "Default value"])
        else:
            print self.conf.get(arg)

    def do_set(self, arg):
        """Set a pysql parameter"""
        if arg=="":
            self.do_get("all")
        else:
            try:
                (key, value)=arg.split("=")
                self.conf.set(key, value)
            except ValueError, e:
                self.help_set()

    def do_write(self, arg):
        """Write configuration to disj"""
        self.conf.write()

    # Shell execution
    def do_shell(self, arg):
        """Execute a shell command or open a shell"""
        # An empty command line enables to open a subshell
        if arg=="":
            if os.name=="posix":
                arg=os.path.expandvars("$SHELL")
            elif os.name=="nt":
                arg="cmd"
            else:
                raise PysqlNotImplemented()
        # Running command line
        exitStatus=os.system(arg)
        # Display exit status if an error occurred
        if exitStatus!=0:
            print CYAN+"Exited with code "+str(exitStatus)+RESET

    def do_lls(self, arg):
        """A simple local ls"""
        self.__checkArg(arg, "<=1")
        if os.name=="posix":
            cmd="ls "
        elif os.name=="nt":
            cmd="dir "
        else:
            raise PysqlNotImplemented()
        # Running command line
        if len(arg)==0:
            exitStatus=os.system(cmd)
        else:
            exitStatus=os.system(cmd+arg)
        # Display exit status if an error occurred
        if exitStatus!=0:
            print CYAN+"Exited with code "+str(exitStatus)+RESET

    def do_lcd(self, arg):
        """Change local directory"""
        self.__checkArg(arg, "<=1")
        if arg=="":
            if os.name=="posix":
                arg=os.path.expandvars("$HOME")
            elif os.name=="nt":
                arg=os.path.expandvars("$HOMEDRIVE")+os.path.expandvars("$HOMEPATH")
            else:
                raise PysqlNotImplemented()
        try:
            os.chdir(arg)
        except OSError:
            raise PysqlException(_("No such directory"))

    def do_lpwd(self, arg):
        """Display current work directory"""
        self.__checkArg(arg, "==0")
        print os.getcwd()


    # Script execution
    def do_script(self, arg):
        """Execute an external sql file, similar to sql*plus @"""
        self.__checkConnection()
        self.__checkArg(arg, "==1")
        try:
            # If file does not exist, tries with .sql extension
            if os.access(arg, os.R_OK):
                fileName=arg
            else:
                fileName=arg+".sql"
            script=file(fileName, "r") # File is closed by GC
            for line in script.readlines():
                line=line.rstrip("\n")
                line = self.precmd(line)
                self.onecmd(line)
                self.postcmd(None, line)
        except IOError, e:
            raise PysqlException(e)

    # Command repeating
    def do_watch(self, arg):
        """Repeat a command"""
        self.__checkConnection()
        self.__checkArg(arg, ">=1")
        # Checks if interval is given
        interval=arg.split()[0]
        try:
            interval=int(interval)
            arg=" ".join(arg.split()[1:])
        except ValueError:
            # Default to 3 secondes
            interval=3
        try:
            while True:
                self.onecmd(arg)
                sleep(interval)
        except KeyboardInterrupt:
            # As for now KeyboardInterrupt is never raised
            # if if cx_Oracle.connection object is created
            # Bug!
            print _("exit watch")
            pass

    # To file
    def do_csv(self, arg):
        """Dumps sql request to file"""
        self.__checkConnection()
        self.__checkArg(arg, ">=3")
        (fileName, sql)=match("(.+?)\s(.+)", arg).groups()
        self.__executeSQL(sql, output="csv", fileName=fileName)

    # Time it!
    def do_time(self, arg):
        """Time request execution time"""
        self.__checkConnection()
        self.__checkArg(arg, ">=3")
        start=time()
        self.__executeSQL(arg, output="null")
        elapsed=time()-start
        print GREEN+_("(Executed in %.1f second(s))") % elapsed + RESET

    # Show it!
    def do_show(self, arg):
        """Show parameters"""
        self.__checkConnection()
        self.__checkArg(arg, ">=1")
        argList=arg.split()
        argList[0]=argList[0].lower()
        if argList[0] in ("parameter", "parameters"):
            self.__checkArg(arg, "<=2")
            param=""
            if len(argList)==2:
                param=argList[1]
            (header, result)=pysqlfunctions.showParameter(self.db, param)
            self.__displayTab(result, header)
        elif argList[0] in ("spparameter", "spparameters"):
            self.__checkArg(arg, "<=2")
            param=""
            if len(argList)==2:
                param=argList[1]
            (header, result)=pysqlfunctions.showServerParameter(self.db, param)
            self.__displayTab(result, header)
        elif argList[0]=="instance":
            self.__checkArg(arg, "==1")
            print _("Connected to ")+self.db.getDSN()
        elif argList[0]=="version":
            self.__checkArg(arg, "==1")
            print _("Oracle ")+self.db.getVersion()
        else:
            print RED+_("Invalid argument")+RESET

    # Time to say bye
    def do_exit(self, arg):
        """ Close current connection and exit pysql"""
        return self.__exit()

    # Command help definitions (in alphabetic order)
    def help_compare(self):
        """online help"""
        print CYAN+_("Usage:")
        print _("\tto compare two schema:\n\t\tcompare user/password@SID user'/password'@SID'")
        print _("\tto compare two tables:\n\t\tcompare user/password@SID:table user'/password'@SID':table'")
        print _("\tto compare two tables in current schema:\n\t\tcompare table table'") +RESET
        print _("By default, only structure is compared.")
        print _("""To compare table data use the "data" keyword like this:""")
        print CYAN+_("\t\tcompare data user/password@SID:table user'/password'@SID':table'")+RESET

    def help_connect(self):
        """online help"""
        print CYAN+_("Usage:\n\tconn[ect] user[/password][@[host[:port]/]SID] [sysdba|sysoper]")+RESET
        print _("Connects to Oracle and closes previous connection if any")

    def help_count(self):
        """online help"""
        print CYAN+_("Usage:\n\tcount <table/view name>")+RESET
        print _("Counts the number of lines in a table or a view")

    def help_datafile(self):
        """online help"""
        self._help_for_search_method("datafile")

    def help_directory(self):
        """online help"""
        self._help_for_search_method("directory")

    def help_disconnect(self):
        """online help"""
        print CYAN+_("Usage:\n\tdisc[connect]")+RESET
        print _("Closes current connection if any")


    def help_edit(self):
        """online help"""
        print CYAN+_("Usage:\n\ted[it] <object name>")+RESET
        print _("Edit (view or modify) an object)")
        print _("If no arg is provided, edits last SQL statement")

    def help_exit(self):
        """online help"""
        print _("Well, it seems rather explicit, isn't it?")

    def help_explain(self):
        """online help"""
        print CYAN+_("Usage:\n\texplain <sql statement>")+RESET
        print _("Computes and displays explain plan for the statement")

    def help_function(self):
        """online help"""
        self._help_for_search_method("function")

    def help_get(self):
        """online help"""
        print CYAN+_("Usage:\n\tget <key>")+RESET
        print _("Prints the value of the parameter <key>")
        print _("The special key « all » allows to print all parameters")

    def help_help(self):
        """online help"""
        print CYAN+_("Usage:\n\thelp <pysql command>")+RESET
        print _("Brings some help like usage and a short description")
        print _("about the command and its parameters")

    def help_history(self):
        """online help"""
        print CYAN+_("Usage:\n\th[istory] <n>")+RESET
        print _("Without any argument, prints the last 20 commands")
        print _("If argument is supplied, executes the nth command")

    def help_index(self):
        """online help"""
        self._help_for_search_method("index")

    def help_kill(self):
        """online help"""
        print CYAN+_("Usage:\n\tkill session-id session-serial")+RESET
        print _("Kills the session given in parameter")
        print _("Uses the 'session' command to find session-id and session-serial (two first columns)")

    def help_last(self):
        """online help"""
        print CYAN+_("Usage:\n\tlast <number of lines>")+RESET
        print _("Fetches all lines of current result set and display only the last lines")
        print _("Default number of lines default to cursor array size")

    def help_library(self):
        """online help"""
        print CYAN+_("Usage:\n\tlib[rary] <sqlName> <sqlText>")+RESET
        print _("Handles user custom sql library. Allow user to save and recall")
        print _("sql requests")
        print _("Sample usage: ")
        print _("\tTo see all saved request: lib")
        print _("\tTo save a request as 'employeeNumber': ")
        print _("\t\tlib employeeNumber select count(*) from employee")
        print _("\trecall a saved request: lib employeNumber")
        print _("\tTo remove the foo request: lib foo remove")

    def help_lock(self):
        """online help"""
        print CYAN+_("Usage:\n\tlock")+RESET
        print _("Displays the locked objects")

    def help_next(self):
        """online help"""
        print CYAN+_("Usage:\n\tnext <number of lines>")+RESET
        print _("Fetches the n next lines of current result set")
        print _("Default number of lines default to cursor array size")
        print _("Just press enter is equivalent to next without arguments")

    def help_package(self):
        """online help"""
        self._help_for_search_method("package")

    def help_procedure(self):
        """online help"""
        self._help_for_search_method("procedure")

    def help_script(self):
        """online help"""
        print CYAN+_("Usage:\n\t@ <script>")+RESET
        print _("Executes a PL/SQL script and displays the output on the standard output")

    def help_set(self):
        """online help"""
        print CYAN+_("Usage:\n\tset <key>=<value>")+RESET
        print _("Sets <value> to the parameter <key>")

    def help_sequence(self):
        """online help"""
        self._help_for_search_method("sequence")

    def help_shell(self):
        """online help"""
        print CYAN+_("Usage:\n\t! <command line>")+RESET
        print _("Executes a command into the system terminal (depending on your system profile)")
        print _("If no commands are given then a subshell is openned")

    def help_lcd(self):
        """online help"""
        print CYAN+_("Usage:\n\tlcd <path>")+RESET
        print _("Changes working directory")

    def help_lls(self):
        """online help"""
        print CYAN+_("Usage:\n\tlls [path/][file]")+RESET
        print _("Lists directory contents")

    def help_lpwd(self):
        """online help"""
        print CYAN+_("Usage:\n\tlpwd")+RESET
        print _("Prints local directory")

    def help_segment(self):
        """online help"""
        self._help_for_search_method("segment")

    def help_show(self):
        """online help"""
        print CYAN+_("Usage:\n\tshow instance")+RESET
        print _("Displays the database service name (DSN) of the current connection")
        print CYAN+_("Usage:\n\tshow version")+RESET
        print _("Displays the database server version")
        print CYAN+_("\n\tshow parameter[s] <partial parameter name>")+RESET
        print _("Looks for session parameters with name like the partial name given")
        print _("Wilcard % can be used. ")
        print _("If none is provided, pysql adds a % at the begining and the end")
        print CYAN+_("\n\tshow spparameter[s] <partial parameter name>")+RESET
        print _("Looks for server parameters with name like the partial name given.")
        print _(" These parameters are defined in spfile. Wilcard % can be used.")
        print _("If none is provided, pysql adds a % at the begining and the end")

    def help_table(self):
        """online help"""
        self._help_for_search_method("table")

    def help_tablespace(self):
        """online help"""
        self._help_for_search_method("tablespace")

    def help_trigger(self):
        """online help"""
        self._help_for_search_method("trigger")

    def help_user(self):
        """online help"""
        self._help_for_search_method("user")

    def help_view(self):
        """online help"""
        self._help_for_search_method("view")

    def help_watch(self):
        """online help"""
        print CYAN+_("Usage:\n\twatch <n> <pysql cmd or sql order>")+RESET
        print _("Repeats the command each n seconds")
        print _("If n is ommited, repeat each 3 seconds")

    def help_write(self):
        """online help"""
        print _("Writes configuration to disk")
        print _("Path is $HOME/.pysql/pysqlrc on Unix, %APPDATA%/pysql/pysqrc on Windows")
        print _("This command takes no argument")

    def _help_for_search_method(self, searchObject):
        """generic online help all object search method"""
        print CYAN+_("Usage:\n\t%s <search pattern on %s name>") % (searchObject, searchObject)+RESET
        print _("Looks for %s which match the search pattern") % searchObject
        print _("Wilcard % and boolean operators (and/or) can be used.")
        print _("If a single word and no % is provided, pysql adds a % at the begining and the end")
        print _("Ex. : %s FOO or (BAR%% and %%TEST%%)") % searchObject


    # Helper functions (private so start with __ to never override any superclass methods)
    def __addToCompleteList(self, wordList, theme="general"):
        """Adds wordList the completion list "theme"
        @param wordList: list of item to completion
        @param theme: string theme
        @return: None
        """
        if not self.conf.completeLists.has_key(theme):
            # Creates the theme
            self.conf.completeLists[theme]=[]

        for word in [unicode(j).upper() for j in wordList]:
            if word not in self.conf.completeLists[theme]:
                self.conf.completeLists[theme].append(word)
        # Keeps completeList small by truncating to the 100 last words
        limit=self.conf.get("completionListSize")
        self.conf.completeLists[theme]=self.conf.completeLists[theme][-limit:]

    def __getCompletionItems(self, text, themes=["general"], prefix=""):
        """Returns list of item matching text for lists of theme
        @param text: word to match for completion
        @type text: string
        @param themes: list of theme of completion to user
        @type themes: list of string
        @param prefix: text prefix that should be add to completed text
        @return:list of string"""
        completeList=[]
        for theme in themes:
            try:
                completeList+=self.conf.completeLists[theme]
            except KeyError:
                # Some theme can be undefined. No pb
                pass
        return [prefix+i for i in completeList if i.startswith(text.upper())]

    def __connect(self, connectString, mode=""):
        """Calls the PysqlDb class to connect to Oracle"""

        count=connectString.count("@")
        if count==0:
            sid=os.path.expandvars("$ORACLE_SID")
        elif count==1:
            (connectString, sid)=connectString.split("@")
        else:
            raise PysqlException(_("Invalid connection string"))

        count=connectString.count("/")
        if count==0:
            user=connectString
            passwd=getpass()
        elif count==1:
            (user, passwd)=connectString.split("/")
        else:
            raise PysqlException("Invalid connection string")

        connectString=user+"/"+passwd+"@"+sid
        self.db=PysqlDb(connectString, mode)
        self.__setPrompt()

    def __disconnect(self):
        """Disconnects from Oracle and update prompt"""
        if self.db:
            self.db.close()
            self.db=None
        self.__setPrompt()

    def __setPrompt(self, blank=False, finishedQuery=False):
        """Sets the prompt according to the connexion state
        @param blank: if true, no prompt is issue (default is False)
        @param finishedQuery: if true mark prompt with a * to notify a query is finished
        @type blank: bool
        @type finishedQuery: bool"""
        #TODO: do not update title for every line
        codec=self.conf.getCodec()
        if blank:
            prompt=""
        else:
            if self.db is None:
                prompt=self.notConnectedPrompt
                # Update the title (without color else it is a huge mess)
                setTitle(_("Pysql - Not connected"), codec)
            else:
                prompt=self.db.getUsername()+"@"+self.db.getDSN()+" "
                if finishedQuery:
                    prompt+="* "
                setTitle("Pysql - %s" % prompt, codec)
        self.prompt=prompt.encode(codec, "replace")

    def __searchObjet(self, objectType, objectName):
        """Searches Oracle object"""
        self.__checkConnection()
        # Looks for schema in object name. Default is all (%)
        objectOwner="%"
        # Try to find owner if a dot is provided
        try:
            (objectOwner, objectName)=objectName.split(".")
        except ValueError:
            pass
        objectOwner=objectOwner.upper()
        # If no name if given, searches for all
        if objectName=="":
            objectName="%"
        if self.conf.get("case_sensitive")=="no":
            objectName=objectName.upper()
        result=pysqlfunctions.searchObject(self.db, objectType, objectName, objectOwner)
        for owner in result.keys():
            print GREEN+("***** %s *****" % owner)+RESET
            self.__addToCompleteList(result[owner], objectType)
            self.__displayCol(result[owner])

    def __displayCol(self, listOfString):
        """Displays on column the list of strings"""
        # If terminal width is not set, use a default of 120 (should read real term width !)
        termWidth=self.conf.get("termWidth")
        #BUG: columnize does not support unicode.
        listOfString=[i.encode(self.conf.getCodec(), "replace") for i in listOfString]
        self.columnize(listOfString, displaywidth=termWidth)

    def __displayTab(self, array, header=None):
        """Displays in tabular the array using correct width for each column"""
        termWidth=int(self.conf.get("termWidth")) # Terminal maximum width
        widthMin=int(self.conf.get("widthMin"))   # Minimum size of the column
        transpose=(self.conf.get("transpose")=="yes")
        shrink=(self.conf.get("shrink")=="yes")
        colsep=self.conf.get("colsep")
        if colsep=="space":
            colsep=" "

        nbLine=len(array)
        if len(array)==0:
            print CYAN+"(no result)"+RESET
            return
        nbColumn=len(array[0]) # Yes, we suppose it to be a real array

        if header:
            # Adds description header
            array.insert(0, header)
            nbLine+=1

        if transpose:
            # Transposes result!
            array=[[array[i][j] for i in range(len(array))] for j in range(nbColumn)]
            # Computes new nbColumn & nbLine
            nbLine=nbColumn
            nbColumn=len(array[0])

        # Convert None to NULL
        for i in xrange(nbLine):
            for j in xrange(nbColumn):
                if array[i][j] is None:
                    array[i][j]="NULL"

        # Computes width max of each column (comprehension list are cool)
        width=[max([itemLength(i[j]) for i in array]) for j in range(nbColumn)]
        shrinked=False     # have we shrinked the result set ?
        widthMax=max(width)
        if shrink:
            while sum(width)+nbColumn>=termWidth and widthMax>widthMin:
                # Result set too large, need to shrink a little
                # Shrinking the bigger by 1 character
                shrinked=True
                widthMax=max(width)
                width[width.index(widthMax)]=widthMax-1

        # If header, add pretty line just above
        if header and not transpose:
            array.insert(1, ["-"*width[i] for i in range(nbColumn)])

        # Goes for printing
        coloredLines=0
        for line in array:
            if header and coloredLines<2 and not transpose:
                # Colorizes header only
                sys.stdout.write(GREY+BOLD)
                coloredLines+=1
            for i in range(nbColumn):
                if header and i==0 and transpose:
                    # colorize the first column
                    sys.stdout.write(GREY+BOLD)
                # Quite stupid to test this for each line...
                #TODO: Should be done one time before looping on each line
                if isinstance(line[i], (int, long, float)):
                    print str(line[i])[:width[i]].rjust(width[i]),
                else:
                    print line[i][:width[i]].ljust(width[i]),
                if header and i==0 and transpose:
                    print RESET,
                sys.stdout.write(colsep) # Adds colsep
            print RESET
        if shrinked:
            # Warns the user
            print CYAN+_("(some columns have been shrinked to fit your terminal size)")+RESET

    def __checkConnection(self):
        """Raises an exception is there's no connection defined
        The test is light (db object defined), no real connection test
        is done."""
        if self.db is None:
            raise PysqlException(_("Not connected to Oracle"))

    def __checkArg(self, arg, argTest):
        """Checks if arg respect argTest else raise a PysqlException
        @param arg: argument to check. Blank is the arg separator
        @type arg: str or list of str
        @param argTest: test with syntaxe like: ">2", "==1", "<=3"
        @type argTest: str
        @return: None
        """
        #TODO: move this to helpers
        if match("=\d+", argTest):
            # Bouh, replace the single = by ==
            argTest="="+argTest
        if isinstance(arg, basestring):
            arg=arg.split()
        try:
            if not eval(unicode(len(arg)) + argTest):
                raise PysqlException(_("Invalid argument. Use help <command name> for usage"))
        except SyntaxError, e:
            raise PysqlException(_("Invalid syntax for argument checking"))

    def __executeSQL(self, sql, output="screen", fileName="pysql.csv"):
        """Executes SQL request
        @param sql: SQL request to executed
        @type sql: str
        @param output: output type. Only affect select queries. Null means all result are sent to paradise
        @type output: str (screen, csv, xml or null)
        @param fileName: name of the file for csv and xml extract
        @type fileName: str"""

        self.__checkConnection()
        if len(sql)<2:
            raise PysqlException("SQL command is too short")

        # Saves it for further editing (with edit command for example) or recall with /
        self.lastStatement=sql

        # Background query?
        if sql[-1]=="&":
            sql=sql.rstrip("&")
            query=BgQuery(self.db.getConnectString(), sql, self.exceptions)
            query.start()
            self.bgQueries.append(query)
            print GREEN+_("Background query launched")+RESET
            return

        # Choosing command with the first keyword
        keyword=sql.upper().split()[0]
        if keyword.startswith("SELECT"):
            if output=="screen":
                (result, moreRows)=self.db.execute(sql)
                self.__toScreen(result, moreRows)
            elif output=="csv":
                self.db.execute(sql, fetch=False)
                self.__toCsv(fileName)
                print GREEN+"(Completed)" +RESET
            elif output=="xml":
                raise PysqlNotImplemented()
            elif output=="null":
                self.db.execute(sql, fetch=False)
                for i in self.db.getCursor().fetchmany():
                    pass
            else:
                raise PysqlException(_("Unknown output type !"))
        elif keyword.startswith("INSERT"):
            lines=self.db.execute(sql)
            print GREEN+unicode(lines) + _(" line(s) inserted")+RESET
        elif keyword.startswith("UPDATE"):
            lines=self.db.execute(sql)
            print GREEN+unicode(lines) + _(" line(s) updated")+RESET
        elif keyword.startswith("DELETE"):
            lines=self.db.execute(sql)
            print GREEN+unicode(lines) + _(" line(s) deleted")+RESET
        elif (keyword.startswith("DROP")
           or keyword.startswith("CREATE")
           or keyword.startswith("TRUNCATE")
           or keyword.startswith("ALTER")
           or keyword.startswith("ANALYZE")
           or keyword.startswith("BEGIN")
           or keyword.startswith("DECLARE")
           or keyword.startswith("COMMENT")
           or keyword.startswith("EXECUTE")
           or keyword.startswith("GRANT")
           or keyword.startswith("REVOKE")):
            self.db.execute(sql)
            print GREEN+ _("Statement executed")+RESET
            result=self.db.getServerOuput()
            # Print the ouput (if exist)
            for line in result:
                print line
        else:
            print RED+BOLD+_("Unknown command or sql order. Type help for help")+RESET

    def __toScreen(self, result, moreRows):
        """Displays first part of fetch on screen
        @param result: array of tabular data
        @type result: list of list of str
        @param moreRows: indicates if there's more data to fetching
        @type moreRows: bool
        """
        if result:
            self.__displayTab(result, self.db.getDescription())
        else:
            print CYAN+"(no result)"+RESET

        if moreRows:
            self.fetching=True
            print CYAN+_("(press enter to see next results)")+RESET
        else:
            self.fetching=False

    def __toCsv(self, fileName):
        """Write query result to a file"""
        try:
            fileHandle=file(fileName, "w")
            csv_writer = csv.writer(fileHandle, dialect="excel")
            csv_writer.writerow(self.db.getDescription()) # Header
            for line in self.db.getCursor():
                csv_writer.writerow(line)
        except Exception, e:
            raise PysqlException(e)

    def __fetchNext(self, nbLines=0):
        """ Fetches next result of current cursor"""
        (result, moreRows)=self.db.fetchNext(nbLines)
        self.__toScreen(result, moreRows)

    def __exit(self):
        """ Closes current connection and exits pysql"""
        if len(self.exceptions)>0:
            print CYAN+_("******* Error sum up *******")+RESET
            errors=[(e.getTimeStamp(), e.msg.replace("\n", " "), e.oraCode) for e in self.exceptions]
            self.__displayTab(errors, ("Date", "Error message", "Oracle error Code"))

        print CYAN+_("\n\nBye !\n")+RESET

        rc=0
        # Flushes completion cache to disk
        try:
            self.conf.writeCache()
        except PysqlException, e:
            print e
            rc=1
        # Flushes history to disk
        try:
            self.conf.writeHistory()
        except PysqlException, e:
            print e
            rc=1
        # Flushes sql library to disk
        try:
            self.conf.writeSqlLibrary()
        except PysqlException, e:
            print e
            rc=1
        try:
            self.__disconnect()
        except PysqlException, e:
            print e
            rc=1

        self.rc=rc
        return True

    # Complete functions aliases
    complete_conn=complete_connect
    complete_lib=complete_library

    # Functions aliases
    aliases={"conn" : "connect",
             "dep"  : "dependencies",
             "desc" : "describe",
             "disc" : "disconnect",
             "du"   : "diskusage",
             "ed"   : "edit",
             "exec" : "execute",
             "h"    : "history",
             "lib"  : "library",
             "start": "script",
             "q"    : "exit",
             "quit" : "exit"
            }