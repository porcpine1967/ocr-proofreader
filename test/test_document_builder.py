#!/usr/bin/env python
import Image
import unittest
import os

PATH = os.path.split(os.path.realpath(__file__))[0]

import document_builder
import spell_checker
from test_helper import test_expected

PATH = os.path.split(os.path.realpath(__file__))[0]
class DocumentBuilderTester(unittest.TestCase):
    def test_fixed_words(self):
        sc = spell_checker.StubSpellChecker([
            'Cantrip',
            'government',
            'bomb',
            'born',
            'bod',
            "he'll",
            'What',
            'hiss',
        ])
        db = document_builder.SpellcheckDocMaker(sc)
        for test, expected in test_expected('{}/test_spellcheck/fix_spelling'.format(PATH)):
            self.assertEqual(db.fixed_words((test,)).values()[0], [expected,])

        
    def test_checkables(self):
        to_test = (
            ('bad', 'company', ['badcompany', 'bacompany',]),
            ('bad-', 'company', ['badcompany',]),
            ("bad'", 'company', ['badcompany',]),
            ('bad', 'Company', []),
            (u'ba\u00E0', 'company', [u'ba\u00E0company', 'bacompany',]),
            ('bad', u'\u00E0ompany', [u'bad\u00E0ompany', u'ba\u00E0ompany',]),
            ('ba', 'company', [],),
            ('bad', 'com', ['badcom', 'bacom',],),
            ('bad', 'co', [],),
            )
        db = document_builder.SpellcheckDocMaker(spell_checker.StubSpellChecker([]))        
        for word1, word2, expected in to_test:
            self.assertEqual(spell_checker.joinables(word1, word2), expected)

    def test_page_info(self):
        pi = document_builder.PageInfo('{}/test_paragraphs/images/straight.pbm'.format(PATH),
                                        '{}/test_paragraphs/text/straight.txt'.format(PATH))
        page_lines = pi.line_guess()
        self.assertEquals(len(pi.lines), len(page_lines))

        pi = document_builder.PageInfo('{}/test_paragraphs/images/slanted.pbm'.format(PATH),
                                        '{}/test_paragraphs/text/slanted.txt'.format(PATH))
        page_lines = pi.line_guess()
        self.assertEquals(len(pi.lines), len(page_lines))

        pi = document_builder.PageInfo('{}/test_paragraphs/images/maigret.pbm'.format(PATH),
                                        '{}/test_paragraphs/text/maigret.txt'.format(PATH))
        page_lines = pi.line_guess()
        self.assertEquals(len(pi.lines), len(page_lines))
        
