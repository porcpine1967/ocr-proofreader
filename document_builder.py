#!/usr/bin/env python
""" This module creates useful documents for cleaning."""

import codecs
import os
import re

import spell_checker
from regex_helper import REGEX_LETTER, REGEX_CAPITAL, REGEX_SMALL

begins_with_lowercase = re.compile(REGEX_SMALL, re.UNICODE).match
ends_with_lowercase = re.compile(u'{}$'.format(REGEX_SMALL), re.UNICODE).match

class SpellcheckDocMaker(object):
    """ Creates documents that can later be used for spell checking."""
    def __init__(self, spell_checker, output_dir='working'):
        self.spell_checker = spell_checker
        self.output_dir = output_dir
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
    def make_word_fix_doc(self, dir_):
        checker = self.spell_checker
        bad_words = set()
        for fn in os.listdir(dir_):
            if fn.endswith('.txt'):
                for bad_word in checker.check_document('{}/{}'.format(dir_, fn)):
                    bad_words.add(spell_checker._decode(bad_word))
        fixes = self.fixed_words(bad_words)
        with codecs.open('{}/word_fixes.txt'.format(self.output_dir), mode='wb', encoding='utf-8') as f:
            for bad_word, good_version in fixes.items():
                f.write(u'{}|{}\n'.format(bad_word, good_version))

    def make_line_join_doc(self, dir_):
        """Creates a document of fixes for cross-line joining.
        Uses all the documents found in dir_
        Writes to 'hyphen_fixes' in current directory
        with the format:
        joinedwords|comma-separated-fixes
        """
        checker = self.spell_checker
        fixes = set()
        hold_word = ''
        for fn in os.listdir(dir_):
            if fn.endswith('.txt'):
                with codecs.open('{}/{}'.format(dir_, fn), mode='r', encoding='utf-8') as f:
                    for l in f:
                        words = l.split()
                        if len(words): # ignore blank lines
                            fixes.update(self.checkables(hold_word, words[0]))
                            if len(words) > 1:
                                hold_word = words[-1]
                            else:
                                hold_word = ''  
        
        # need this to maintain order when checking
        fixes_array = list(fixes)
        with codecs.open('{}/hold_words.tmp'.format(self.output_dir), mode='wb', encoding='utf-8') as f:
            f.write(u' xNoTPassx '.join(fixes_array))
        
        failed_joins = checker.check_document('{}/hold_words.tmp'.format(self.output_dir))
        modified_bad_words = u''.join([spell_checker._decode(w) for w in failed_joins]).split(u'xNoTPassx') 
        good_changes = {}
        bad_words = set()
        for idx, w in enumerate(fixes_array):
            if modified_bad_words[idx]:
                bad_words.add(spell_checker._decode(w))
            else:
                good_changes[w] = w
        for bad_word, good_change in self.fixed_words(bad_words).items():
            good_changes[bad_word] = good_change
        with codecs.open('{}/line_join_fixes.txt'.format(self.output_dir), mode='wb', encoding='utf-8') as f:
            for bad_word, good_version in good_changes.items():
                    f.write(u'{}|{}\n'.format(bad_word, good_version))

    def fixed_words(self, bad_words):
        """ Takes a list of bad words and returns a dictionary of the 
        bad words that can be fixed mapped to the unique fix.

        bad words with multiple fixes are ignored.
        """
        checker = self.spell_checker
        good_changes = {}
        for bad_word in bad_words:
            changed_versions = checker.transformed_variations(bad_word)
            good_versions = []
            if changed_versions:
                changed_words = [t[0] for t in changed_versions]
                with codecs.open('{}/hold_words.tmp'.format(self.output_dir), mode='wb', encoding='utf-8') as f:
                    f.write(u' xNoTPassx '.join(changed_words))
                # aspell maintains order of bad words, but does not return good words
                # we therefore need some way to indicate that nothing was returned
                # (that is the word was good) in a given area.  This is notede by
                # a repetition of xNoTPassx
                # We then split on that, which leaves empty strings in the space
                # that have good words (which fail a boolean test in python)
                failed_versions = checker.check_document('{}/hold_words.tmp'.format(self.output_dir))
                words_if_bad = u''.join([spell_checker._decode(w) for w in failed_versions]).split(u'xNoTPassx')
                for idx, w in enumerate(changed_words):
                    if not words_if_bad[idx]:
                        good_versions.append(spell_checker._decode(w))
                if len(good_versions) == 1:
                    good_changes[bad_word] = good_versions[0]
        return good_changes
    def checkables(self, first_word, second_word):
        """ Sees if it would be worth while joining the word.

        returns an array of words to check.
        """
        words_to_check = []
        if begins_with_lowercase(second_word) \
            and len(first_word) > 2 \
            and len(second_word) > 2:
            if ends_with_lowercase(first_word):
                words_to_check.append(first_word + second_word)
            words_to_check.append(first_word[:-1] + second_word)
        return words_to_check
        
