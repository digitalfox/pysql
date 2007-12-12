#!/usr/bin/python
# -*- coding: utf-8 -*-

# Sébastien Renard (sebastien.renard@digitalfox.org)
# Code licensed under GNU GPL V2

"""PySQL daemon mode
Principle is quite simple. You start pysql as a daemon on one
machine with Oracle client and pysql installed, then, everyone
with a simple telnet client (like putty or telnet.exe on windows
and legacy telnet on netcat on Unix) can use pysql !

This is intended for machine without Oracle client or
without python (sad people !).
"""

# Python imports
import socket
from threading import Thread
from telnetlib import DO, DONT, ECHO, IAC, NAWS, NEW_ENVIRON, SB, SE, SGA, TTYPE, WILL
# PySQL imports
from pysqlshell import PysqlShell
from pysqlexception import PysqlException
from pysqlio import PysqlIO


def pysqlNet(port, maxClient):
    """Pysql daemon mode main interface"""
    #create an INET, STREAMing socket
    serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        serverSocket.bind((socket.gethostname(), port))
    except socket.error, e:
        raise PysqlException(_("Cannot create socket : %s") % e)
    #become a server socket
    serverSocket.listen(maxClient)
    try:
        while True:
            # Wait for client and create a PysqlNetClient for each one
            (clientSocket, address) = serverSocket.accept()
            client = PysqlNetClient(clientSocket)
            client.start()
            #TODO: use a list to store client socket to shutdown properly
    except KeyboardInterrupt:
        print "Receive keyboard interrupt. Waiting for client ending"
        print "Hit control-C again to exit immediately"
        serverSocket.close()
        #TODO: close client sockets also !
        return 0
class PysqlNetClient(Thread):
    """Interface for each pysqlNet client"""

    def __init__(self, clientSocket):
        """Client initialisation"""
        Thread.__init__(self)
        self.setDaemon(False)
        stdout=PysqlIO("socket")
        stdout.setSocket(clientSocket)
        self.shell=PysqlShell(completekey="tab", stdout=stdout, stdin=None)
        self.socket=clientSocket
    
    def __del__(self):
        """End client connection"""
        print "End of client"
        
    def run(self):
        """Action !"""
        print "New client"
        self.setCharacterMode()
        self.netLoop()
        self.socket.close()
    
    def setCharacterMode(self):
        """Initialise the telnet client to use character mode"""
        #self.sendCommand(WILL, ECHO)
        #self.sendCommand(DONT, ECHO)
        self.sendCommand(DO, NAWS)
        self.sendCommand(WILL, SGA)
        self.sendCommand(DO, SGA)
        self.sendCommand(DO, TTYPE)
        self.sendCommand(DO, NEW_ENVIRON)

    def sendCommand(self, verb, option):
        """Send telnet option negociation"""
        self.socket.send(IAC)
        self.socket.send(verb)
        self.socket.send(option)

    def read(self):
        """Read socket input stream and separate data from options
        @return: data or null string if option is read"""
        char=self.socket.recv(1)
        subOptions=[]
        if char==IAC:
            #TODO: handle IAC IAC (IAC escape)
            verb=self.socket.recv(1)
            option=self.socket.recv(1)
            if verb==SB:
                # Sub negociation
                char=""
                while char!=SE:
                    char=self.socket.recv(1)
                    subOptions.append(char)
                subOptions.remove(SE)
                subOptions.remove(IAC)
            print "option received : %s (%s), %s (%s)" % (verb, ord(verb), option, ord(option))
            if subOptions:
                print "Sub options : %s" % [ord(i) for i in subOptions]
        else:
            # Receive data
            return char
    
    def write(self, data):
        """Write data through socket and escape command if needed
        @param data: data to be sent
        @type data: str
        """
        if IAC in data:
            data=data.replace(IAC, IAC+IAC)
        self.socket.send(data)

    def netLoop(self):
        """Simulate the standard cmd loop() method for network purpose"""
        self.shell.preloop()
        endOfLoop=False
        endOfLine=False
        while not endOfLoop:
            lineBuffer=[] # List buffer to store the command line we are receiving
            endOfLine=False
            self.write(self.shell.prompt)
            while not endOfLine:
                char=self.read()
                if not char:
                    break
                print "receive : |%s| (%s) " % (char, ord(char))
                if char==chr(4) and len(lineBuffer)==0:
                    # Receive control-D (EOF) at the begining of the line. Exiting
                    print "Get EOF"
                    lineBuffer=["EOF"]
                    break
                if char in ("\n", "\r"):
                    char=self.read()
                    print "receive (for end of line) : |%s| (%s) " % (char, ord(char))
                    if char in ("\n", "\r", chr(0)): # Why chr(0) and not \r ??
                        endOfLine=True
                    else:
                        print "\r without \n or vice versa - strange. Skipping to next line"
                        endOfLine=True
                else:
                    # Store char
                    lineBuffer.append(char)
            line="".join(lineBuffer)
            print "sending : |%s|" % line
            line=self.shell.precmd(line)
            endOfLoop=self.shell.onecmd(line)
            endOfLoop=self.shell.postcmd(endOfLoop, line)
            self.shell.postloop()
        print "end of loop"