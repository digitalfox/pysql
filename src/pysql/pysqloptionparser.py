# -*- coding: utf-8 -*-
"""
An OptionParser which accepts a single string as input and raise an exception
instead of calling sys.exit() in case of error

Kindly borrowed from Yokadi Option parser (http://github.com/agateau/yokadi/)
@author: Aurélien Gâteau <aurelien.gateau@free.fr>
@author: Sébastien Renard <Sebastien.Renard@sigitalfox.org>

@license: GNU GPL V3
"""
from optparse import OptionParser
import sys
from pysqlexception import PysqlException, PysqlOptionParserNormalExitException


class PysqlOptionParser(OptionParser):
    def __init__(self):
        OptionParser.__init__(self, add_help_option=False)

    def parse_args(self, line):
        argv = line.split(u" ")
        # Splitting an empty line gives us [""], not an empty array
        if argv == [u""]:
            argv = []

        # Remove extra spaces
        argv = [i for i in argv if i is not u""]

        return OptionParser.parse_args(self, argv)

    def exit(self, status=0, msg=None):
        if msg:
            sys.stderr.write(msg)
        if status == 0:
            raise PysqlOptionParserNormalExitException()
        else:
            raise PysqlException(msg)

    def error(self, msg):
        self.print_usage()
        raise PysqlException(msg)