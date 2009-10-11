#!/usr/bin/python
# -*- coding: utf-8 -*-

"""This module defines all pysql exceptions
@author: Sébastien Renard (sebastien.renard@digitalfox.org)
@license: GNU GPL V3
"""

# Python imports
from time import ctime, time
from re import match

class PysqlException(Exception):
    """Pysql Exceptions"""
    def __init__(self, exception):
        # instance members
        self.oraCode=""
        self.msg=""
        self.time=None

        # TimeStamp exception
        self.time=time()

        # Sets default message
        self.msg=unicode(exception)

        # Gets ORA error code if this is an Oracle exception
        if isinstance(exception, PysqlException):
            self.msg=exception.msg
            self.oraCode=exception.oraCode
            self.time=exception.time
        else:
            result=match("(.*)(ORA-\d+): (.*)", unicode(exception))
            if result:
                self.oraCode=result.group(2)
                self.msg=result.group(1)+result.group(3)

        # Calls father constructor
        Exception.__init__(self, exception)

    def getTimeStamp(self):
        """@return: exception creation timestamp as a formated string"""
        return ctime(self.time)

    def __str__(self):
        if self.oraCode=="":
            return self.msg
        else:
            return self.oraCode +"-" + self.msg

class PysqlNotImplemented(PysqlException):
    """Indicates function not yet implemented"""
    def __init__(self):
        PysqlException.__init__(self, _("Not yet implemented"))

class PysqlActionDenied(PysqlException):
    """Indicates user is not granted to perform this action"""
    def __init__(self, message):
        PysqlException.__init__(self, _("Action denied: %s") % message)

class PysqlOptionParserNormalExitException(Exception):
    """
    A dummy exception which makes it possible to have --help exit silently
    """
    pass
