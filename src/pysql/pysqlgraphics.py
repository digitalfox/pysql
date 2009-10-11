#!/usr/bin/python
# -*- coding: utf-8 -*-

""" This module defines all high level graphical functions of pysql
@author: Sébastien Delcros (Sebastien.Delcros@gmail.com)
@author: Sébastien Renard (sebastien.renard@digitalfox.org)
@license: GNU GPL V3
"""

# pylint: disable-msg=E1101

# Python imports:
import os
import sys
import re
import subprocess
from math import log, sqrt

# Pysql imports:
from pysqlqueries import datamodelSql, dependenciesSql, diskusageSql
from pysqlexception import PysqlException, PysqlActionDenied
from pysqlcolor import BOLD, CYAN, GREEN, GREY, RED, RESET
from pysqlconf import PysqlConf
from pysqloraobjects import OraObject
from pysqlhelpers import convert, generateWhere, getProg, removeComment, which

# High level pysql graphical functions
def datamodel(db, userName, tableFilter=None, withColumns=True):
    """Extracts the datamodel of the current user as a picture
The generation of the picture is powered by Graphviz (http://www.graphviz.org)
through the PyDot API (http://www.dkbza.org/pydot.html)
@param db: pysql db connection
@param userName: schema to be extracted
@param tableFilter: filter pattern (in pysql extended syntax to extract only some tables (None means all)
@param withColumns: Indicate whether columns are included or not in datamodel picture
"""
    # Tries to import pydot module
    try:
        from pydot import find_graphviz, Dot, Edge, Node
    except ImportError:
        message=_("Function not available because pydot module is not installed.\n\t")
        message+=_("Go to http://dkbza.org/pydot.html to get it.")
        raise PysqlException(message)

    # Reads conf
    conf=PysqlConf.getConfig()
    format=conf.get("graph_format") # Output format of the picture
    fontname=conf.get("graph_fontname") # Font used for table names
    fontsize=conf.get("graph_fontsize") # Font size for table names
    fontcolor=conf.get("graph_fontcolor") # Color of table and column names
    tablecolor=conf.get("graph_tablecolor") # Color of tables
    bordercolor=conf.get("graph_bordercolor") # Color of tables borders
    linkcolor=conf.get("graph_linkcolor") # Color of links between tables
    linklabel=conf.get("graph_linklabel") # Display constraints name or not

    # Gets picture generator
    prog=getProg(find_graphviz(), conf.get("graph_program"), "fdp")

    graph=Dot(overlap="false", splines="true")

    # Tables, columns and constraints (temporary and external tables are excluded. So are TOAD tables)
    if tableFilter:
        whereClause=generateWhere("table_name", tableFilter)
    else:
        whereClause="1=1"
    tables=db.executeAll(datamodelSql["tablesFromOwner"] % (userName, whereClause))
    nbTables=len(tables)
    if nbTables==0:
        raise PysqlException(_("No table found. Your filter clause is too restrictive or the schema is empty"))
    tableList=", ".join(["'%s'" % table[0] for table in tables]) # Table list formated to be used in SQL query
    print CYAN+_("Extracting %d tables...      ") % nbTables +RESET,
    current=0
    for table in tables:
        tableName=table[0]
        content="""<<TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0">"""
        content+="""\n<TR><TD PORT="%s">""" % tableName
        content+="""<FONT FACE="%s" POINT-SIZE="%f" COLOR="%s">""" % (fontname, fontsize, fontcolor)
        content+=tableName
        content+="</FONT></TD></TR>"
        if withColumns:
            columns=db.executeAll(datamodelSql["columnsFromOwnerAndTable"], [userName, tableName])
            for column in columns:
                columnName=column[0]
                columnType=column[1]
                content+="""\n<TR><TD ALIGN="LEFT" PORT="%s_%s">""" % (tableName, columnName)
                content+="""<FONT FACE="%s" POINT-SIZE="%f" COLOR="%s">""" % \
                         (fontname, fontsize-2, fontcolor)
                if column[2] is None: # Normal field
                    content+=" "
                else: # Primary key field
                    content+="PK%d" % int(column[2])
                content+=" %s (%s)" % (columnName, columnType)
                content+="</FONT></TD></TR>"
        content+="\n</TABLE>>"
        graph.add_node(Node(tableName, shape="none", label=content, style="filled", \
                            fillcolor=tablecolor, color=bordercolor))
        current+=1
        sys.stdout.write("\b\b\b\b\b%4.1f%%" % round(100*float(current)/nbTables, 1))
        sys.stdout.flush()

    print
    # Links between tables (foreign key -> primary key)
    # Only extract links from considered tables
    links=db.executeAll(datamodelSql["constraintsFromOwner"] % (userName, tableList, tableList))
    nbLinks=len(links)
    print (CYAN+_("Extracting %d links...      ") % nbLinks +RESET),
    current=0
    for link in links:
        if linklabel=="yes":
            graph.add_edge(Edge(src=link[1], dst=link[2], color=linkcolor))
        else:
            graph.add_edge(Edge(src=link[1], dst=link[2], label=link[0], color=linkcolor, \
                                fontcolor=linkcolor, fontname=fontname, fontsize=str(fontsize-3)))
        current+=1
        sys.stdout.write("\b\b\b\b\b%4.1f%%" % round(100*float(current)/nbLinks, 1))

    print
    filename=db.getDSN()+"_"+userName+"."+format
    generateImage(graph, filename, prog, format)
    viewImage(filename)

def dependencies(db, objectName, direction, maxDepth, maxNodes):
    """Displays object dependencies as a picture
The generation of the picture is powered by Graphviz (http://www.graphviz.org)
through the PyDot API (http://www.dkbza.org/pydot.html)
@param db: pysql db connection
@param objectName: name of the oracle object on which dependancies are computed
@param direction: direction of the dependancy graph. Can be "onto", "from" or "both"
@param maxDepth: Override default maxDepth value. If None, use default value
@param maxNodes: Override default maxNodes value. If None, use default value
"""
    # Tries to import pydot module
    try:
        from pydot import find_graphviz, Dot, Edge, Node
    except ImportError:
        message=_("Function not available because pydot module is not installed.\n\t")
        message+=_("Go to http://dkbza.org/pydot.html to get it.")
        raise PysqlException(message)

    # Reads conf
    conf=PysqlConf.getConfig()
    format=conf.get("graph_format") # Output format of the picture
    fontname=conf.get("graph_fontname") # Font used for object names
    fontsize=conf.get("graph_fontsize") # Font size for object names

    # Gets picture generator
    prog=getProg(find_graphviz(), conf.get("graph_program"), "dot")

    graph=Dot(overlap="false", splines="true", rankdir="TB")

    if direction=="onto" or direction=="from":
        dirList=[direction]
    elif direction=="both":
        dirList=["onto", "from"]
    else:
        dirList=[]

    for currentDir in dirList:
        depth=0
        objectList=[OraObject(objectName=objectName)]
        objectList[0].guessInfos(db)
        objectOwner=objectList[0].getOwner()
        objectName=objectList[0].getName()
        objectType=objectList[0].getType()
        label=objectOwner+"."+objectName+"\\n("+objectType+")"
        graph.add_node(Node(objectName, label=label, fontname=fontname, fontsize=str(fontsize), shape="diamond"))
        nodeList=[objectName]
        edgeList=[]
        nextObjectList=[]

        while objectList!=[] and depth<=maxDepth and len(nodeList)<=maxNodes:
            depth+=1
            for currentObject in objectList:
                currentObjectOwner=currentObject.getOwner()
                currentObjectName=currentObject.getName()
                if currentDir=="onto":
                    # Objects referencing the the current object
                    result=db.executeAll(dependenciesSql["refOnFromOwnerAndName"], \
                                        [currentObjectOwner, currentObjectName])
                elif currentDir=="from":
                    # Objects referenced by the the current object
                    result=db.executeAll(dependenciesSql["refByFromOwnerAndName"], \
                                        [currentObjectOwner, currentObjectName])
                refObjectList=[OraObject(objectOwner=i[0], objectName=i[1]) for i in result]
                for currentRefObject in refObjectList:
                    currentRefObject.guessInfos(db)
                    currentRefObjectOwner=currentRefObject.getOwner()
                    currentRefObjectName=currentRefObject.getName()
                    currentRefObjectType=currentRefObject.getType()
                    if not currentRefObjectName in nodeList:
                        nodeList.append(currentRefObjectName)
                        # Object shape
                        if currentRefObjectType in ("TABLE", "VIEW", "SEQUENCE"):
                            shape="box"
                        elif currentRefObjectType in ("PACKAGE", "FUNCTION", "PROCEDURE", "TRIGGER"):
                            shape="ellipse"
                        else:
                            shape="none"
                        # Object label
                        if currentRefObjectOwner==db.getUsername().upper():
                            label=currentRefObjectName
                        else:
                            label=currentRefObjectOwner+"."+currentRefObjectName
                        label+="\\n("+currentRefObjectType+")"
                        # Adding object to graph
                        graph.add_node(Node(currentRefObjectName, label=label, fontname=fontname, \
                                                                  fontsize=str(fontsize), shape=shape))
                    if not [currentObjectName, currentRefObjectName] in edgeList:
                        if currentDir=="onto":
                            edgeList.append([currentObjectName, currentRefObjectName])
                            graph.add_edge(Edge(dst=currentObjectName, src=currentRefObjectName, \
                                                color="red"))
                        elif currentDir=="from":
                            edgeList.append([currentObjectName, currentRefObjectName])
                            graph.add_edge(Edge(src=currentObjectName, dst=currentRefObjectName, \
                                                color="darkgreen"))
                nextObjectList+=refObjectList
            objectList=nextObjectList
            nextObjectList=[]

        if len(nodeList)>maxNodes:
            print RED+"Warning: Reach max node, references lookup stopped on direction %s" % currentDir +RESET
        if depth>maxDepth:
            print RED+"Warning: Reach max recursion limit, references lookup stopped on direction %s" % currentDir +RESET

    filename="dep_"+objectOwner+"."+objectName+"."+format
    generateImage(graph, filename, prog, format)
    viewImage(filename)


def diskusage(db, userName, withIndexes=False):
    """Extracts the physical storage of the current user as a picture based on Oracle statistics
The generation of the picture is powered by Graphviz (http://www.graphviz.org)
through the PyDot API (http://www.dkbza.org/pydot.html)
"""
    # Tries to import pydot module
    try:
        from pydot import find_graphviz, Dot, Subgraph, Cluster, Edge, Node
    except ImportError:
        message=_("Function not available because pydot module is not installed.\n\t")
        message+=_("Go to http://dkbza.org/pydot.html to get it.")
        raise PysqlException(message)

    # Reads conf
    conf=PysqlConf.getConfig()
    unit=conf.get("unit") # Unit used to format data
    format=conf.get("graph_format") # Output format of the picture
    fontname=conf.get("graph_fontname") # Font used for table names
    fontsize=conf.get("graph_fontsize") # Font size for table names
    fontcolor=conf.get("graph_fontcolor") # Color of table and column names
    tablecolor=conf.get("graph_tablecolor") # Color of tables
    indexcolor=conf.get("graph_indexcolor") # Color of indexes
    bordercolor=conf.get("graph_bordercolor") # Color of borders

    # Gets picture generator
    prog=getProg(find_graphviz(), conf.get("graph_program"), "fdp")

    graph=Dot(type="dirgraph", overlap="false", splines="true")

    # Tablespaces
    if userName==db.getUsername().upper():
        tablespaces=db.executeAll(diskusageSql["Tablespaces"])
    else:
        tablespaces=db.executeAll(diskusageSql["TablespacesFromOwner"], [userName])
    for tablespace in tablespaces:
        tablespaceName=unicode(tablespace[0])
        subGraph=Subgraph("cluster_"+tablespaceName, label=tablespaceName, bgcolor="palegreen")
        graph.add_subgraph(subGraph)
        # Tables
        if userName==db.getUsername().upper():
            tables=db.executeAll(diskusageSql["TablesFromTbs"], [tablespaceName])
        else:
            tables=db.executeAll(diskusageSql["TablesFromOwnerAndTbs"], [userName, tablespaceName])
        nbTables=len(tables)
        print CYAN+_("Extracting %3d tables from tablespace %s") % (nbTables, tablespaceName) +RESET
        for table in tables:
            tableName=table[0]
            if table[1] is None:
                print BOLD+RED+_("""Warning: table "%s" removed because no statistics have been found""") \
                           % (tableName) +RESET
                continue
            if table[1]==0:
                print BOLD+RED+_("""Warning: table "%s" removed because it is empty""") \
                           % (tableName) +RESET
                continue
            num_rows=int(table[1])
            avg_row_len=float(table[2])
            size=int(convert(table[3], unit))

            # Mathematics at work
            height=round(log(num_rows)/10, 3)
            width=round(sqrt(avg_row_len)/5, 3)
            label=tableName +"\\n("+str(size)+" %s)" % unit.upper()
            subGraph.add_node(Node(tableName, label=label, shape="box", style="filled", \
                                   color=bordercolor, fillcolor=tablecolor, \
                                   fontname="arial", fontcolor=fontcolor, fontsize=str(fontsize-2), \
                                   fixedsize="true", nodesep="0.01", height=str(height), width=str(width)))
        if not withIndexes:
            continue
        # Indexes
        if userName==db.getUsername().upper():
            indexes=db.executeAll(diskusageSql["IndexesFromTbs"], [tablespaceName])
        else:
            indexes=db.executeAll(diskusageSql["IndexesFromOwnerAndTbs"], [userName, tablespaceName])
        nbIndexes=len(indexes)
        print CYAN+_("Extracting %3d indexes from tablespace %s") % (nbIndexes, tablespaceName) +RESET
        for index in indexes:
            indexName=index[0]
            if index[1] is None:
                print BOLD+RED+_("""Warning: index "%s" removed because no statistics have been found.""") \
                           % (indexName) +RESET
                continue
            if index[1]==0:
                print BOLD+RED+_("""Warning: index "%s" removed because it is empty""") \
                           % (indexName) +RESET
                continue
            num_rows=int(index[1])
            distinct_keys=int(index[2])
            size=int(convert(index[3], unit))
            tableName=str(index[4])

            # Mathematics at work again
            height=round(log(num_rows)/10, 3)
            width=round(log(distinct_keys)/10, 3)
            label=indexName +"\\n("+str(size)+" %s)" % unit.upper()
            #print "tablespace="+tablespaceName+"; index="+indexName+ \
            # "; height="+str(height)+"; width="+str(width)
            subGraph.add_node(Node(indexName, label=label, shape="box", style="filled", \
                                   color=bordercolor, fillcolor=indexcolor, \
                                   fontname="arial", fontcolor=fontcolor, fontsize=str(fontsize-2), \
                                   fixedsize="true", nodesep="0.01", height=str(height), width=str(width)))
            # Invisible edges for placement purpose only (not very usefull in fact)
            #graph.add_edge(Edge(src=indexName, dst=tableName, constraint="false", style="invis"))

    print
    filename="du_"+userName+"."+format
    generateImage(graph, filename, prog, format)
    viewImage(filename)

def pkgTree(db, packageName):
    """Creates the call tree of internal package functions and procedures"""

    # Tries to import pydot module
    try:
        from pydot import find_graphviz, Dot, Edge, Node
    except ImportError:
        message=_("Function not available because pydot module is not installed.\n\t")
        message+=_("Go to http://dkbza.org/pydot.html to get it.")
        raise PysqlException(message)

    # Reads conf
    conf=PysqlConf.getConfig()
    format=conf.get("graph_format") # Output format of the picture
    fontname=conf.get("graph_fontname") # Font used for functions names
    fontsize=conf.get("graph_fontsize") # Font size for functions names
    fontcolor=conf.get("graph_fontcolor") # Color of functions names

    # Gets picture generator
    prog=getProg(find_graphviz(), conf.get("graph_program"), "fdp")

    package=OraObject(objectName=packageName)
    package.guessInfos(db)

    graph=Dot(overlap="false", splines="true")

    # Lists of function or procedure
    verbs=[]

    # Tries to resolve synonym and describe the target
    #TODO: factorise this code!!
    if package.getType()=="SYNONYM":
        package=package.getTarget(db)
        if package.getType()=="SYNONYM":
            raise PysqlException("Too much synonym recursion")

    if package.getType() not in ("PACKAGE", "PACKAGE BODY"):
        raise PysqlException(_("This is not a package or package not found"))

    # Gets package body content
    package.setType(u"PACKAGE BODY")
    print CYAN+_("Extracting package source...")+RESET
    content=package.getSQLAsList(db)

    # Removes comments
    print CYAN+_("Parsing source and building graph...")+RESET
    newContent=[]
    comment=False
    for line in content:
        line, comment=removeComment(line, comment)
        newContent.append(line)
    content=newContent

    # Gets procedures and functions
    for line in content:
        result=re.match("\s*(FUNCTION|PROCEDURE)\s+(.+?)[\s|\(]+", line, re.I)
        if result:
            verbs.append(re.escape(result.group(2)))
            graph.add_node(Node(result.group(2).upper(), shape="box", label=result.group(2).upper(), \
                                fontsize=str(fontsize), fontname=fontname, fontcolor=fontcolor))

    if not verbs:
        raise PysqlException(_("This package does not have any readable function or procedure"))

    verbs="|".join(verbs)
    # Gets call of functions/procedure inside each other
    currentVerb=""
    for line in content:
        # Doesn't pay attention to end lines
        if re.match("\s*END.*;", line, re.I):
            continue
        # Marks the function/procedure we are parsing
        result=re.match("\s*(FUNCTION|PROCEDURE)\s+(.+?)[\s|\(]+", line, re.I)
        if result:
            currentVerb=result.group(2)
            continue # else we get a circular reference below ;-)
        result=re.match(".*\s(%s).*" % verbs, line, re.I)
        if result:
            if graph.get_edge(currentVerb.upper(), result.group(1).upper()) is None:
                graph.add_edge(Edge(src=currentVerb.upper(), dst=result.group(1).upper()))

    filename=package.getName()+"_dep."+format
    generateImage(graph, filename, prog, format)
    viewImage(filename)

def viewImage(imagePath):
    """Shows Image with prefered user image viewer
@param imagePath: path to image file"""
    conf=PysqlConf.getConfig()
    viewer=conf.get("graph_viewer")
    if viewer=="off":
        return
    elif viewer=="auto":
        if os.name=="nt":
            viewers=("mspaint.exe",)
        else:
            viewers=("gwenview", "kview", "kuickshow", "eog", "gthumb", "gimp", "firefox")
        for viewer in viewers:
            viewer=which(viewer)
            if viewer is not None:
                break
    else:
        viewer=which(viewer)
    if viewer is not None:
        subprocess.Popen([viewer, imagePath], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    else:
        raise PysqlException(_("Viewer was not found"))

def generateImage(graph, filename, prog, format):
    """Generate graphviz image from graph
@param graph: pydot graph object
@param filename: image filename (str)
@param format: image format (str)
"""
    print CYAN+_("Generating picture using %s filter...") % prog +RESET
    import pydot
    try:
        graph.write(filename, prog=prog, format=format)
    except (IOError, OSError, pydot.InvocationException), e:
        raise PysqlException("Graphviz failed to generate image:\n%s" % e)
    print GREEN+_("Image saved as ")+filename+RESET

