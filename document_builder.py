#!/usr/bin/env python
""" This module creates useful documents for cleaning."""

from collections import Counter
import codecs
import Image
import os
import re
import sys

import spell_checker
from regex_helper import REGEX_LETTER, REGEX_CAPITAL, REGEX_SMALL

begins_with_lowercase = re.compile(REGEX_SMALL, re.UNICODE).match
ends_with_lowercase = re.compile(u'.*{}$'.format(REGEX_SMALL), re.UNICODE).match
punctuation_stripper = re.compile(u'.*?({}.*{}).*'.format(REGEX_LETTER, REGEX_LETTER), re.UNICODE).match

class SpellcheckDocMaker(object):
    """ Creates documents that can later be used for spell checking."""
    def __init__(self, spell_checker, output_dir='working', delimiter='|'):
        self.spell_checker = spell_checker
        self.output_dir = output_dir
        self.delimiter = delimiter
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

    def letters(self, word):
        """ Returns the word with for-and-aft punctuation stripped."""
        m = punctuation_stripper(word)
        if m:
            return m.group(1)
        else:
            return word
    def possible_headers(self, dir_):
        headers = {}
        for fn in os.listdir(dir_):
            if fn.endswith('.txt'):
                with codecs.open('{}/{}'.format(dir_, fn), mode='r', encoding='utf-8') as f:
                    for l in f:
                        if len(l.strip()) > 5:
                            headers[fn] = l.strip()
                            break
        with codecs.open('{}/headers.txt'.format(self.output_dir), mode='wb', encoding='utf-8') as f:
            for page, header in sorted(headers.items(), key=lambda x: int(x[0][:-4])):
                f.write(u'{}|{}\n'.format(page, header))

    def make_possible_proper_name_doc(self, dir_):
        proper_nouns = set()
        hold_word = ''
        for fn in os.listdir(dir_):
            if fn.endswith('.txt'):
                with codecs.open('{}/{}'.format(dir_, fn), mode='r', encoding='utf-8') as f:
                    for l in f:
                        words = l.split()
                        if len(words): # ignore blank lines
                            for word in words:
                                if self.spell_checker.proper_noun(hold_word, word):
                                    proper_nouns.add(self.letters(word))
                                hold_word = word
        with codecs.open('{}/possible_proper_nouns.txt'.format(self.output_dir), mode='wb', encoding='utf-8') as f:
            for proper_noun in proper_nouns:
                f.write(u'{}\n'.format(proper_noun))
        
    def make_word_fix_doc(self, dir_):
        checker = self.spell_checker
        bad_words = set()
        for fn in os.listdir(dir_):
            if fn.endswith('.txt'):
                for bad_word in checker.check_document('{}/{}'.format(dir_, fn)):
                    bad_words.add(spell_checker._decode(bad_word))
        fixes = self.fixed_words(bad_words)
        with codecs.open('{}/word_fixes.txt'.format(self.output_dir), mode='wb', encoding='utf-8') as f:
            for bad_word, good_versions in fixes.items():
                f.write(u'{}|{}\n'.format(bad_word, self.delimiter.join(good_versions)))

    def make_line_join_doc(self, dir_):
        """Creates a document of fixes for cross-line joining.
        Uses all the documents found in dir_
        Writes to 'hyphen_fixes' in current directory
        with the format:
        joinedwords|delimiter-separated-fixes
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
                            fixes.update(self.joinables(hold_word, words[0]))
                            # blank out the hold word if only one word in line
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
            for bad_word, good_versions in good_changes.items():
                    f.write(u'{}|{}\n'.format(bad_word, self.delimiter.join(good_versions)))

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
                # (that is the word was good) in a given area.  This is noted by
                # a repetition of xNoTPassx
                # We then split on that, which leaves empty strings in the space
                # that have good words (which fail a boolean test in python)
                failed_versions = checker.check_document('{}/hold_words.tmp'.format(self.output_dir))
                words_if_bad = u''.join([spell_checker._decode(w) for w in failed_versions]).split(u'xNoTPassx')
                for idx, w in enumerate(changed_words):
                    if not words_if_bad[idx]:
                        good_versions.append(spell_checker._decode(w))
                if good_versions:
                    good_changes[bad_word] = good_versions
                    
        return good_changes

    def joinables(self, first_word, second_word):
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
        
    def page_image_info(self, dir_):
        pass

class PageInfo(object):
    """ Maps an image to its text."""
    def __init__(self, path_to_image, path_to_text):
        self.path_to_image = path_to_image
        self.path_to_text = path_to_text
        self.load_text_data()
        self.load_image_data()

    def load_text_data(self):
        self.lines = []
        with codecs.open(self.path_to_text, mode='rb', encoding='utf-8') as f:
            for l in f:
                line = l.strip()
                if line:
                    self.lines.append(l)

    def load_image_data(self):
        self.pixel_lines = []
        im = Image.open(self.path_to_image)
        self.width, height = im.size
        current_row = []
        for pixel in im.getdata():
            current_row.append(pixel)
            if not len(current_row) % self.width:
                self.pixel_lines.append(PixelLineInfo(current_row))
                current_row = []

    def chop_by_leap_forward(self, minimum_leap, minimum_height, header_offset):
        lines = []
        current_line = LineInfo(0)
        last_left_margin = None
        for idx, pixel_line in enumerate(self.pixel_lines):
            if idx < header_offset:
                continue
            if not last_left_margin:
                check_line = False
            else:
                leap = last_left_margin - pixel_line.left_margin > minimum_leap
                check_line = leap or pixel_line.blank
            last_left_margin = pixel_line.left_margin
            if check_line:
                if len(current_line.pixel_lines) > minimum_height:
                    lines.append(current_line)
                current_line = LineInfo(idx)
            current_line.add_pixel_line(pixel_line)
        return lines

    def line_guess(self, header_offset=0):
        """ Tries to guess where the lines of text in the image are.

        header_offset: if there is gunk at the beginning
        you don't want to count."""
        lines = []
        minimum_jump = self.width
        minimum_height = 1
        while len(lines) != len(self.lines) and 0 < minimum_jump:
            lines = self.chop_by_leap_forward(minimum_jump, minimum_height, header_offset)
            # minimum height is 20% of average
            minimum_height = sum([line.height for line in lines])/(len(lines)*5)
            minimum_jump -= 10
        return lines


    def chopped_version(self, output_file_path, header_offset=0):
        """ Outputs one file per line.

        output_file_path should have a {} to hold
        the line index.
        """
        im = Image.open(self.path_to_image)
        width, height = im.size
        for idx, line in enumerate(self.line_guess(header_offset)):
            image_page_b = im.crop((0, line.y, width, line.y + line.height))
            image_page_b.save(output_file_path.format(idx))
            
class LineInfo(object):
    def __init__(self, y):
        self.pixel_lines = []
        self.height = 0
        self.left_margin = None
        self.y = y
        self.width = None

    def add_pixel_line(self, pixel_line):
        self.pixel_lines.append(pixel_line)
        self.height = len(self.pixel_lines)
        if self.left_margin:
            self.left_margin = min(self.left_margin, pixel_line.left_margin)
        else:
            self.left_margin = pixel_line.left_margin
        if not self.width:
            self.width = pixel_line.full_length
    def blank(self):
        for pixel_line in self.pixel_lines:
            if not pixel_line.blank:
                return False
        return True

class PixelLineInfo(object):
    """ Information about a given line of pixels."""
    def __init__(self, data):
        self.full_length = len(data)
        if 0 in data:
            self.left_margin = data.index(0)
            self.blank = False
        else:
            self.left_margin = self.full_length
            self.blank = True
        self.density = float(data.count(0))/self.full_length

