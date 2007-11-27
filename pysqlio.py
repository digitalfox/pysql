#!/usr/bin/python
# -*- coding: utf-8 -*-

# Sébastien Renard (sebastien.renard@digitalfox.org)
# Code licensed under GNU GPL V2

"""This module contains the PysqlIO"""

# Pysql imports
from pysqlexception import PysqlException

# Python import
import sys

class PysqlIO:
    """Simple and uniform interface for IO to screen and network"""
    
    # PysqlIO instance (singleton)
    ioInstance=None
    
    def __init__(self, target="screen"):
        """PysqlIO initialisation."""
        self.target=None
        self.socket=None
        self.codec="latin-1" # default
        
        self.setTarget(target)
 
    def getIOHandler(cls):
        """Factory for PysqlIO instance singleton
        @return: PysqIO instance"""
        if cls.ioInstance is None:
            cls.ioInstance=PysqlIO()
        return cls.ioInstance
    getIOHandler=classmethod(getIOHandler)

    def setCodec(self, codec):
        """Define codec to be used to encode output"""
        self.codec=codec

    def setTarget(self, target): 
        """Define IO target
        @arg target: IO target can be screen (default) or socket"""
        if target in ("screen", "socket", "null"):
            self.target=target
        else:
            raise Exception(_("Invalid PysqlIO target. Aborting"))
       
    def setSocket(self, socket):
        """Define the client socket for socket output. This is useless for screen target"""
        self.socket=socket
    
    def read(self):
        """@return: string read from user input (socket or stdin). \n is choped"""
        if self.target=="screen":
            return sys.stdin.readline().strip("\n")
        elif self.target=="socket":
            return self.socket.recv()

    def write(self, line, lineReturn=False, encode=True):
        """Encode and output line to target"""
        if self.target=="null":
            return
        if type(line)!="unicode" and encode:
            line=unicode(line)
        if lineReturn:
            line+="\n"
        if encode:
            line=line.encode(self.codec, "replace")
        if self.target=="screen":
            sys.stdout.write(line)
            sys.stdout.flush()
        elif self.target=="socket":
            # We assume we are in server mode and this is a socket
            try:
                self.socket.send(line)
            except Exception, e:
                raise PysqlException(_("Error while writting in socket : %s") % e)

    def writeln(self, line):
        """Write line with line return. See write() for details"""
        self.write(line, lineReturn=True)
        
    def __call__(self, line):
        """Method to use class as a callable object"""
        self.write(line, lineReturn=True)