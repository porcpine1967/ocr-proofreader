#!/usr/bin/env python

import unittest
import os
import shutil
import sys
PATH = os.path.split(os.path.realpath(__file__))[0]
sys.path.append('{}/..'.format(PATH))

from document_builder import LineInfo
from line_manager import LineManager, SubstitutionManager, Line
from line_manager import Word, Page, NoWordException
from spell_checker import StubSpellChecker, AspellSpellChecker
from spell_checker import EnglishSpellFixer
from test_helper import test_expected

class LineManagerTester(unittest.TestCase):
    def setUp(self):
        os.chdir('{}/test_line_manager'.format(PATH)) 
    
    def test_average(self):
        lm = LineManager(StubSpellChecker(()), verbose=False)
        lm.load('avg_test')
        self.assertEqual(25, lm.average_length)

    def test_page_numbers(self):
        lm = LineManager(StubSpellChecker(()), verbose=False)
        lm.load('avg_test')
        self.assertEqual(['1', '2', '3',], lm.page_numbers)


    def test_last_word(self):
        for test, expected in test_expected('last_word'):
            line = Line(test, 1, StubSpellChecker(()))
            self.assertEqual(line.last_word(), expected)
    def test_first_word(self):
        for test, expected in test_expected('first_word'):
            line = Line(test, 1, StubSpellChecker(()))
            self.assertEqual(line.first_word(), expected)

    def test_fix_hyphen(self):
        sp = StubSpellChecker(('the', 'rains', 'in', 'spain', 'fall',),
            {'sp-_ain': 'spain'})
        line_one = Line('the rains in sp-', 1, sp)
        line_two = Line('ain fall', 2, sp)
        lm = LineManager(sp, verbose=False)
        lm.fix_hyphen((line_one, line_two))
        self.assertEqual('the rains in spain', line_one.text)
        self.assertEqual('fall', line_two.text)

    def test_fix_lines(self):
        sp = StubSpellChecker(('the', 'rains', 'in', 'spain', 'fall', 'spa-n',),
            {'sp-_ain': 'spain', 'ra-_ins' : 'rains'})
        lm = LineManager(sp, verbose=False)
        lm.load('hyphen_test')
        lm.fix_lines()

        page_one = ' '.join([line.text for line in lm.pages['1']])
        page_two = ' '.join([line.text for line in lm.pages['2'] if line.valid])
        self.assertEquals('the rains in spain fall spaen in spain the rains', page_one)
        self.assertEquals('fall', page_two)

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

    def test_page_has_word(self):
        page = Page('5')
        expected_line = Line('bob has a train', 1, StubSpellChecker(()))
        page.append(expected_line)
        # assert simple match
        line, line_info = page.find_word('has')
        self.assertEquals(expected_line, line)
        self.assertIsNone(line_info)
        next_line = Line('he has no friends', 1, StubSpellChecker(()))
        page.append(next_line)
        # assert picks first line
        line, line_info = page.find_word('has')
        self.assertEquals(expected_line, line)

        # assert can find in second line
        line, line_info = page.find_word('friends')
        self.assertEquals(next_line, line)
        line_info_1 = LineInfo(1)
        line_info_2 = LineInfo(2)
        line_info_3 = LineInfo(3)
        page.line_infos = [line_info_1, line_info_2, line_info_3]
        
        # assert finds correct line info no header
        line, line_info = page.find_word('friends')
        self.assertEquals(line_info_2, line_info)
        
        page.has_header = True
        # assert finds correct line info with header
        line, line_info = page.find_word('friends')
        self.assertEquals(line_info_3, line_info)
        
        # assert raises if not found
        self.assertRaises(NoWordException, page.find_word, 'notinstrings')

if __name__ == '__main__':
    unittest.main()
