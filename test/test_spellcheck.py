#!/usr/bin/env python

import unittest
import os
import shutil
import sys
PATH = os.path.split(os.path.realpath(__file__))[0]

import spell_checker
from test_helper import test_expected

class SpellCheckTester(unittest.TestCase):

    def test_stub(self):
        sc = spell_checker.StubSpellChecker(['a','b','c','d',])
        self.assertEqual(['the', 'cat',], sc.check_line('the b cat c a d'))

    def test_aspell(self):
        sc = spell_checker.AspellSpellChecker('en_US')
        self.assertEqual(['afeve', 'brff',], sorted(sc.check_line('what brff needs is an afeve in the car.')))

    def test_quick_fix(self):
        sc = spell_checker.StubSpellChecker(['a','b','c','d',])
        for test, expected in test_expected('{}/test_spellcheck/quick_fix'.format(PATH)):
            self.assertEqual(sc.quick_fix(test), expected)

    def test_english_quick_fix(self):
        sc = spell_checker.StubSpellChecker(['a','b','c','d',])
        sc.fixer = spell_checker.EnglishSpellFixer()
        for test, expected in test_expected('{}/test_spellcheck/quick_fix'.format(PATH)):
            self.assertEqual(sc.quick_fix(test), expected)
        for test, expected in test_expected('{}/test_spellcheck/english_quick_fix'.format(PATH)):
            self.assertEqual(sc.quick_fix(test), expected)

    def test_fix_spelling(self):
        sc = spell_checker.StubSpellChecker([
            'government',
            'bomb',
            'born',
            'bod',
            "he'll",
            'What',
            'hiss',
        ])
        for test, expected in test_expected('{}/test_spellcheck/fix_spelling'.format(PATH)):
            self.assertEqual(sc.fix_spelling(test), expected)
    def test_odd_punctuation(self):
        sc = spell_checker.StubSpellChecker(['a','b','c','d',])
        for test, expected in test_expected('{}/test_spellcheck/odd_punctuation'.format(PATH)):
            self.assertEqual(sc.odd_punctuation(test), bool(int(expected)), test)
    def test_hyphenate(self):
        sc = spell_checker.StubSpellChecker([
                'pearl-jam',
                'd-lite',
                'de-lite',
        ])
        for test, expected in test_expected('{}/test_spellcheck/hyphenate'.format(PATH)):
            self.assertEqual(sc.hyphenate(test), expected)
if __name__ == '__main__':
    unittest.main()
