#!/usr/bin/env python

import unittest
import os
import shutil
import sys
PATH = os.path.split(os.path.realpath(__file__))[0]
sys.path.append('{}/..'.format(PATH))

from line_manager import LineManager, SubstitutionManager, Line
from line_manager import Word
from spell_checker import StubSpellChecker, AspellSpellChecker
from spell_checker import EnglishSpellFixer
from test_helper import test_expected

class LineManagerTester(unittest.TestCase):
    def setUp(self):
        os.chdir('{}/test_line_manager'.format(PATH)) 
    
    def test_average(self):
        lm = LineManager(StubSpellChecker(()))
        lm.load('avg_test')
        self.assertEqual(25, lm.average_length)

    def test_page_numbers(self):
        lm = LineManager(StubSpellChecker(()))
        lm.load('avg_test')
        self.assertEqual(['1', '2', '3',], lm.page_numbers)

    def test_simple_substitutions(self):
        sm = SubstitutionManager(StubSpellChecker(()))
        for test, expected in test_expected('simple_substitutions'):
            self.assertEqual(sm.update_single_characters(test), expected)        
    def test_word_substitutions(self):
        good_words = (
            u"'Jules",
            u'Jules',
            u'of',
            u'the',
            u'morning',
            u'immediate',
            u'government',
            u'won\'t',
            u'Who',
            u'who',
            u'flying',
            u'to',
            u'So',
            u'I\'d',
            u'on',
            u'flick',
            u'rid',
            u'Soccer',
            u'wordless',
            u'just-being',)
        stub_spell_checker = StubSpellChecker(good_words)
        stub_spell_checker.fixer = EnglishSpellFixer()
        sm = SubstitutionManager(stub_spell_checker)
        for test, expected in test_expected('word_fixes'):
            self.assertEqual(sm.update_words(test), expected)        

    def test_number_substitutions(self):
        good_words = (
            u'looking',
            u'looking-',
            u'he',
            u"won't",
            u'fly\u00E9ng',
            u'is',
            u'so',
            u'big',
            u'So',
            u'what')
        stub_spell_checker = StubSpellChecker(good_words)
        sm = SubstitutionManager(stub_spell_checker)
        for test, expected in test_expected('number_fixes'):
            self.assertEqual(sm.update_numbers(test), expected)        

    def test_last_word(self):
        for test, expected in test_expected('last_word'):
            line = Line(test, 1, StubSpellChecker(()))
            self.assertEqual(line.last_word().text, expected)
    def test_first_word(self):
        for test, expected in test_expected('first_word'):
            line = Line(test, 1, StubSpellChecker(()))
            self.assertEqual(line.first_word().text, expected)

    def test_fix_hyphen(self):
        sp = StubSpellChecker(('the', 'rains', 'in', 'spain', 'fall',))
        line_one = Line('the rains in sp-', 1, sp)
        line_two = Line('ain fall', 2, sp)
        lm = LineManager(sp)
        lm.fix_hyphen((line_one, line_two))
        self.assertEqual('the rains in', line_one.text)
        self.assertEqual('spain fall', line_two.text)

    def test_fix_lines(self):
        sp = StubSpellChecker(('the', 'rains', 'in', 'spain', 'fall', 'spa-n',))
        lm = LineManager(sp)
        lm.load('hyphen_test')
        lm.fix_lines()

        page_one = ' '.join([line.text for line in lm.pages['1']])
        page_two = ' '.join([line.text for line in lm.pages['2'] if line.valid])
        self.assertEquals('the rains in spain fall spaen in spain the', page_one)
        self.assertEquals('rains fall', page_two)

    def test_verify_word(self):
        sc = StubSpellChecker(('bob', 'bo-b'))
        word = Word('bob', sc)
        self.assertFalse(word.misspelled)
        self.assertFalse(word.odd_punctuation)
        self.assertFalse(word.hyphenated)
        word = Word('bobc', sc)
        self.assertTrue(word.misspelled)
        self.assertFalse(word.odd_punctuation)
        self.assertFalse(word.hyphenated)
        word = Word('b;ob', sc)
        self.assertTrue(word.misspelled)
        self.assertTrue(word.odd_punctuation)
        self.assertFalse(word.hyphenated)
        word = Word('bo-b', sc)
        self.assertFalse(word.misspelled)
        self.assertFalse(word.odd_punctuation)
        self.assertTrue(word.hyphenated)

    def test_hyphenate_word(self):
        sc = StubSpellChecker(('abc-def',))
        word = Word('abcAdef', sc)
        self.assertTrue(word.misspelled)
        self.assertFalse(word.hyphenated)
        word.hyphenate()
        self.assertEquals('abc-def', word.text)
        self.assertFalse(word.misspelled)
        self.assertTrue(word.hyphenated)

    def test_correct_word(self):
        sc = StubSpellChecker(('bob',))
        word = Word('bOb', sc)
        self.assertTrue(word.misspelled)
        word.correct_spelling()
        self.assertEquals('bob', word.text)
        self.assertFalse(word.misspelled)

    def test_hyphen_join(self):
        sc = StubSpellChecker(('dob',
                               'bob-',
                               'bob-dob',
                               ))
        word_one = Word('bob-', sc)
        word_two = Word('dob', sc)

        word_two.prepend(word_one)
        self.assertEquals('', word_one.text)
        self.assertEquals('bob-dob', word_two.text)

    def test_hyphen_fix(self):
        sc = StubSpellChecker(('bellfast',
                               ))
        word_one = Word('bell', sc)
        word_two = Word('fast', sc)

        word_two.prepend(word_one)
        self.assertEquals('', word_one.text)
        self.assertEquals('bellfast', word_two.text)

        word_one = Word('bell-', sc)
        word_two = Word('fast', sc)

        word_two.prepend(word_one)
        self.assertEquals('', word_one.text)
        self.assertEquals('bellfast', word_two.text)

        word_one = Word('belle', sc)
        word_two = Word('fast', sc)

        word_two.prepend(word_one)
        self.assertEquals('', word_one.text)
        self.assertEquals('bellfast', word_two.text)

if __name__ == '__main__':
    unittest.main()
