#!/usr/bin/env python

import unittest
import os

PATH = os.path.split(os.path.realpath(__file__))[0]

from comparison_manager import find_bad, space_bounded

class ComparisonManagerTester(unittest.TestCase):
    def test_find_bad(self):
        tests = (
            ('France like a wanted criminal, I do not see that it is',
            'France like a wanted criminal, 1 do not see that it is',
            [('I', '1',),],),

            ('indignation at the affront to his aristocratic name.',
            'in-dignation at the alfront to his aristocratic name.',
            [('', '-',), ('f', 'l',),],),

            ('reaching out to press his hand. "Giovanni, you know',
            'reaching out to press his hand. ."Giovanni, you know',
            [('', '.',),],),

            ('afterwards you are pale and nervous and frightened and',
            'af-terwards you are pale and nervous and frightened and',
            [('', '-',),],),

            ('"Of course, carissima, how should I not? You go away',
            '"Ofcourse, carissirna, how should I not? You go away',
            [('"Of course,', '"Ofcourse,',),('m', 'rn',),],),

            ('"Ofcourse, carissirna, how should I not? You go away',
            '"Of course, carissima, how should I not? You go away',
            [('"Ofcourse,', '"Of course,',),('rn', 'm',),],),
        )
        for clean, raw, expected in tests:
            self.assertEquals(find_bad(clean, raw), expected)
        
    def test_space_indices(self):
        tests = (
            ('abcd efgh ijkl', 3, 'abcd'),
            ('abcd efgh ijkl', 4, 'abcd efgh'),
            ('abcd efgh ijkl', 5, 'efgh'),
            ('abcd efgh ijkl', 9, 'efgh ijkl'),
            ('abcd efgh ijkl', 10, 'ijkl'),
        )        
        for string, idx, expected in tests:
            self.assertEquals(space_bounded(string, idx), expected, idx)

