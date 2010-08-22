#!/usr/bin/python
# -*- coding: utf-8 -*-

"""pysqlhelpers module test suite
@author: Sébastien Renard (sebastien.renard@digitalfox.org)
@license:GNU GPL V3
"""

# Python imports
import unittest
import locale
from tempfile import TemporaryFile
import sys

# Common test pysql tools
import testhelpers
testhelpers.setup()

# Pysql imports
import pysqlhelpers
from pysqlexception import PysqlException

class TestAddWildCardIfNeeded(unittest.TestCase):
    def test_result_with_default_wildcard(self):
        for answer, question in (("%lala%", "lala"), ("lala%", "lala%"), ("%lala", "%lala"),
                                     ("la%la", "la%la")):
            self.assertEqual(answer, pysqlhelpers.addWildCardIfNeeded(question))

    def test_result_with_various_wildcard(self):
        for wildcard in ("", "%", "$", "*"):
            self.assertEqual(wildcard + "cou cou" + wildcard,
                             pysqlhelpers.addWildCardIfNeeded("cou cou", wildcard=wildcard))
            self.assertEqual("cou%scou" % wildcard,
                             pysqlhelpers.addWildCardIfNeeded("cou%scou" % wildcard, wildcard=wildcard))


class TestColorDiff(unittest.TestCase):
    def test_color_diff(self):
        pass

class TestConvert(unittest.TestCase):
    def test_convert(self):
        pass

class TestGetProg(unittest.TestCase):
    def test_get_prog(self):
        pass

class TestItemLength(unittest.TestCase):
    def test_item_length(self):
        pass

class TestGenerateWhere(unittest.TestCase):
    def test_result(self):
        for answer, question in (("table like 'lala'", "lala"),
                                 ("table like 'lala%'", "lala%"),
                                 ("table like 'lala%' or table like 'loulou'", "lala% or loulou"),
                                 ("table like 'lala%' or table not like 'loulou'", "lala% or !loulou"),
                                 ("( table like 'lala%' or table like 'loulou' )", "(lala% or loulou)"),
                                 ("( table like 'lala%' or table like 'loulou' ) and table like 'lala'",
                                  "(lala% or loulou) and lala"),
                                 ("( table like 'lala%' or table like 'loulou' ) and table like 'lala'",
                                  "(   lala%     or   loulou  )  and   lala"),
                                  ("( table like 'lala%' or table like 'loulou' ) and table like 'lala'",
                                  "(lala%  OR loulou ) aNd lala")):
            self.assertEqual(answer,
                         pysqlhelpers.generateWhere("table", question))

    def test_raise(self):
        for faultyFilter in ("foo bar", "!(lala)", "!(lala or loulou)", "! (lala or loulou)",
                             "(lala or loulou", "(lala or loulou))",
                             "(lala or loulou) )", "(lala or loulou ) )", "lala or loulou)",
                             "lala orr loulou", "lala aand loulou", "lala andor loulou", "lala andd loulou"):
            self.assertRaises(PysqlException, pysqlhelpers.generateWhere, "table", faultyFilter)


class TestRemoveComment(unittest.TestCase):
    def test_remove_one_line_comment(self):
        for line in ("--foo", "-- foo", "--foo ", "--foo--", "--foo --", "--", "-- ", "---", "----", "---- foo ",
                     "/**/", "/* */", "/** */", "/* **/", "/***/", "/* lala */", "/*lala */", "/* lala*/", "/*lala*/"):
            unCommentedLine, comment = pysqlhelpers.removeComment(line)
            self.assertFalse(comment)
            self.failUnlessEqual(unCommentedLine.strip(), "")

    def test_remove_one_line_comment_with_sql(self):
        for answer, question in (("sql ", "sql -- lala"),
                                 ("sql ", "sql --lala"),
                                 ("sql", "sql--lala"),
                                 ("sql ", "sql --"),
                                 ("sql", "sql--"),
                                 ("sql", "sql--------"),
                                 ("sql", "sql-- lala --")):
            unCommentedLine, comment = pysqlhelpers.removeComment(question)
            self.assertFalse(comment)
            self.failUnlessEqual(unCommentedLine, answer)

    def test_remove_multiline_comment(self):
        for anwser, lines in (("sql  sql", ("sql /*", "nice comment", "another comment */", "sql")),
                              ("sql  sql sql", ("sql /* begin of comment", "blabla / * ", "*/sql", "sql")),
                              ("sql  sql", ("sql /*", "lala -- ", "comment */", "sql")),
                              ("sql", ("/*", "nice comment", "*/", "sql")),
                              ("sql /*+ smart hint */ sql", ("sql /*+ smart hint */", "sql")),
                              ("sql   /*+ smart hint */  sql", ("sql /* bla */ /*+ smart hint */ /*", "*/", "sql"))):
            result = []
            comment = False
            for line in lines:
                unCommentedLine, comment = pysqlhelpers.removeComment(line, comment)
                if unCommentedLine:
                    result.append(unCommentedLine)
            self.failUnlessEqual(" ".join(result), anwser)


class TestWhich(unittest.TestCase):
    def test_which(self):
        self.failUnlessEqual(pysqlhelpers.which("cp"), "/usr/bin/cp")
        self.failUnlessEqual(pysqlhelpers.which("gabuzomeuhhh"), None)
        self.failUnlessEqual(pysqlhelpers.which(""), None)

class TestWarn(unittest.TestCase):
    def test_warn(self):
        for message in ("", "blabla", "ééà€", u"blabal"):
            #TODO: handle unicode case
            stdout = sys.stdout
            sys.stdout = TemporaryFile()
            pysqlhelpers.warn(message)
            sys.stdout = stdout # restore stdout

class TestPrintStackTrace(unittest.TestCase):
    def test_print_stack_trace(self):
        pass # TODO: implement your test here

class TestSetTitle(unittest.TestCase):
    def test_set_title(self):
        codec = locale.getpreferredencoding()
        for title in ("", "blabla", u"éééé", u"ééàà€€", "éééààà€€€"):
            pysqlhelpers.setTitle(title, codec)

class TestGetTitle(unittest.TestCase):
    def test_get_title(self):
        codec = locale.getpreferredencoding()
        for title in ("", "blabla", u"éééé", u"ééàà€€", "éééààà€€€"):
            pysqlhelpers.setTitle(title, codec)
            self.failIfEqual(title, pysqlhelpers.getTitle())

class TestGetFromClause(unittest.TestCase):
    def test_simple_from(self):
        for tables, line in (({"dual" : "dual" }, "select * from dual"),
                             ({"d" : "dual" }, "select * from dual d"),
                             ({"dual" : "dual", "emp" : "emp" }, "select * from dual, emp"),
                             ({"d" : "dual", "emp" : "emp" }, "select * from dual d, emp"),
                             ({"dual" : "dual" }, "select * from dual where dummy='X'"),
                             ({"dual" : "dual" }, "select * from dual order by 1"),
                             ({"dual" : "dual" }, "select dummy, count(1) from dual group by dummy"),):
            self.failUnlessEqual(tables, pysqlhelpers.getFromClause(line))


    def test_imbricated_from(self):
        for tables, line in (({"dual" : "dual" }, "select * from (select * from dual);"),):
            self.failUnlessEqual(tables, pysqlhelpers.getFromClause(line))


class TestGetKnownTablesViews(unittest.TestCase):
    def test_simple(self):
        refList = ("dual", "emp")
        for tables, line in ((["dual", ], "select * from dual"),
                             (["dual", ], "select * from dual;"),
                             (["dual", ], "select * from dual d"),
                             (["dual", ], "select * from (select * from dual)"),
                             (["dual", "emp"], "select * from dual, emp"),
                             (["dual", "emp"], "select * from dual d, emp"),
                             (["dual", ], "select * from dual where dummy='X'"),
                             (["dual", ], "select * from dual order by 1"),
                             (["dual", ], "select dummy, count(1) from dual group by dummy"),):
            result = pysqlhelpers.getKnownTablesViews(line, refList)
            result.sort()
            self.failUnlessEqual(tables, result)

if __name__ == '__main__':
    unittest.main()
