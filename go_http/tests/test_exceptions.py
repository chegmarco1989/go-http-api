"""
Tests for go_http.exceptions.
"""

from unittest import TestCase

from go_http.exceptions import PagedException


class TestPagedException(TestCase):
    def test_creation(self):
        err = ValueError("Testing Error")
        p = PagedException(u"12345", err)
        self.assertTrue(isinstance(p, Exception))
        self.assertEqual(p.cursor, u"12345")
        self.assertEqual(p.error, err)

    def test_repr(self):
        p = PagedException(u"abcde", ValueError("Test ABC"))
        self.assertEqual(
            repr(p),
            "<PagedException cursor=u'abcde' error=ValueError('Test ABC',)>")

    def test_str(self):
        p = PagedException(u"lmnop", ValueError("Test LMN"))
        self.assertEqual(
            str(p),
            "<PagedException cursor=u'lmnop' error=ValueError('Test LMN',)>")
