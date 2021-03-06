#!/usr/bin/env python

import unittest
import os
import shutil
import subprocess
import sys
PATH = os.path.split(os.path.realpath(__file__))[0]

import spell_checker
from test_helper import test_expected

class SpellCheckTester(unittest.TestCase):

    def test_stub(self):
        sc = spell_checker.StubSpellChecker(['a','b','c','d',])
        self.assertEqual(['the', 'cat',], sc.check_line('the b cat c a d'))

    def test_aspell(self):
        with open('/dev/null', 'wb') as f:
            if not subprocess.call(['which', 'aspell',], stdout=f, stderr=f):
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
            'Cantrip',
            'government',
            'bomb',
            'born',
            'bod',
            "he'll",
            'What',
            'hiss',
            'different',
        ])
        for test, expected in test_expected('{}/test_spellcheck/fix_spelling'.format(PATH)):
            self.assertEqual(sc.fix_spelling(test), expected)
    def test_odd_punctuation(self):
        sc = spell_checker.StubSpellChecker(['a','b','c','d',])
        for test, expected in test_expected('{}/test_spellcheck/odd_punctuation'.format(PATH)):
            self.assertEqual(bool(sc.odd_punctuation(test)), bool(int(expected)), test)
    def test_hyphenate(self):
        sc = spell_checker.StubSpellChecker([
                'pearl-jam',
                'd-lite',
                'de-lite',
        ])
        for test, expected in test_expected('{}/test_spellcheck/hyphenate'.format(PATH)):
            self.assertEqual(sc.hyphenate(test), expected)

    def test_line_transformations(self):
        """ Test
            XO-to-Xo
            5-to-s
            m-to-rn
            1-to-i
            e-to-c
            1-to-l
            rn-to-m
            cl-to-d
            0-to-o
            ck-to-d
            VV-to-W
            u"lll-to-'ll"
            xX-to-x[space]X
            oo-to-co
            n-tilde-to-fi
            fl-to-fi
        """
        sc = spell_checker.StubSpellChecker([])

        # check simple
        self.assertEqual(set(((u'bus', 'bu5', '5-to-s',),)), sc.transformed_variations('bu5'))
        # check double
        expected = set([('bum5', 'burn5', u'rn-to-m'), (u'burns', 'burn5', u'5-to-s'), (u'bums', 'bum5', u'5-to-s')])
        self.assertEqual(expected, sc.transformed_variations('burn5'))

    def test_proper_noun(self):
        sc = spell_checker.StubSpellChecker([])
        to_test = (
            ('', 'Bob', True,),
            ('', "'Bob", True,),
            ('', '"Bob', True,),
            ('now,', 'Bob', True,),
            ('now,', "'Bob", True,),
            ('now,', '"Bob', True,),
            ('now', 'Bob', True,),
            ('now', "'Bob", True,),
            ('now', '"Bob', True,),
            ('', "'bob", False,),
            ('', '"bob', False,),
            ('', 'bob', False,),
            ('.', 'Bob', False),
            ('?', 'Bob', False),
            ('!', 'Bob', False),
            ('."', 'Bob', False),
            ('?"', 'Bob', False),
            ('!"', 'Bob', False),
            ('.\'', 'Bob', False),
            ('?\'', 'Bob', False),
            ('!\'', 'Bob', False),
            )
        for preceding_word, test, expected in to_test:
            self.assertEquals(bool(sc.proper_noun(preceding_word, test)), expected, '{} properness should be {}'.format(test, expected))
    def test_french_check(self):
        to_test = (
            ('.Vaurais', "J'aurais"),
            ('eXchange', 'exchange'),
        )        
                    
        sc = spell_checker.StubSpellChecker([])
        sc.fixer = spell_checker.FrenchSpellFixer()
        for word, variation in to_test:
            tvs = sc.transformed_variations(word)
            self.assertTrue(variation in [s[0] for s in tvs], variation)        
    def test_strict_check(self):
        sc = spell_checker.StubSpellChecker([])
        sc.fixer = spell_checker.FrenchSpellFixer()
        self.assertEquals(set('f'), sc.strict_check('f'))
    def test_garbage_stripper(self):
        words = (
            ("Julia-she", "Julia"),
            ("Bob's", 'Bob'),
        )
        sc = spell_checker.StubSpellChecker([])
        for word, expected in words:
            self.assertEquals(expected, sc.strip_garbage(word))
    def test_proper_nouns(self):
        lines = (
            (u'12 \xab Jai bien connu Bob Gaston Chemineau, dit Angoua', ['Jai', 'Bob', 'Gaston', 'Chemineau', 'Angoua',]),
            (u'12 \xab Jai bien connu Gaston Chemineau, dit Angoua', ['Jai', 'Gaston', 'Chemineau', 'Angoua',]),
            ('I know Tim Smith-Klein', ['Tim', 'Smith', 'Klein',]),
            ('It is true, But it is not True. I thinks so', ['But','True',]),
            ('It is true, But it is not true. I thinks so', ['But',]),
            ('He said, "Anything is fine."', []),
        )
        sc = spell_checker.StubSpellChecker([])
        for line, expected in lines:
            self.assertEquals(sc.proper_nouns(line), expected)
    def test_improper_lower(self):
        lines = (
            ('This is true. but not really', ['but',]),
            ('"Is this true?" he asked.', []),
            ('Is this true? he asked.', ['he', ]),
        )
        sc = spell_checker.StubSpellChecker([])
        for line, expected in lines:
            self.assertEquals(sc.lower_after_sentence(line), expected)

if __name__ == '__main__':
    unittest.main()
