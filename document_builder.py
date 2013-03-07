#!/usr/bin/env python
""" This module creates useful documents for cleaning."""

import codecs
from collections import Counter, defaultdict
import csv
import Image, ImageDraw
import os
import re
import sys

import spell_checker
from regex_helper import REGEX_LETTER, REGEX_CAPITAL, REGEX_SMALL

punctuation_stripper = re.compile(u'.*?({}.*{}).*'.format(REGEX_LETTER, REGEX_LETTER), re.UNICODE).match
ends_with_hyphen = re.compile(r'.*-$', re.UNICODE).match

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
        footers = {}
        for fn in os.listdir(dir_):
            if fn.endswith('.txt'):
                need_header = True
                with codecs.open('{}/{}'.format(dir_, fn), mode='r', encoding='utf-8') as f:
                    for l in f:
                        line = l.strip()
                        if len(line) > 5 and need_header:
                            headers[fn] = line
                            need_header = False
                        if line:
                            footers[fn] = line
        with codecs.open('{}/headers.txt'.format(self.output_dir), mode='wb', encoding='utf-8') as f:
            for page, header in sorted(headers.items(), key=lambda x: int(x[0][:-4])):
                f.write(u'{}|{}\n'.format(page, header))
        with codecs.open('{}/footers.txt'.format(self.output_dir), mode='wb', encoding='utf-8') as f:
            for page, footer in sorted(footers.items(), key=lambda x: int(x[0][:-4])):
                f.write(u'{}|{}\n'.format(page, footer))

    def remove_possible_headers(self, dir_):
        """ Removes the headers that were not manually removed from the possible headers file."""
        header_map = {}
        with codecs.open('{}/headers.txt'.format(self.output_dir), mode='rb', encoding='utf-8') as f:
            for l in f:
                try:
                    page, header = l.strip().split('|', 1)
                    header_map[page] = header
                except ValueError:
                    pass
        footer_map = defaultdict(lambda : 'NOT A LINE')
        with codecs.open('{}/footers.txt'.format(self.output_dir), mode='rb', encoding='utf-8') as f:
            for l in f:
                try:
                    page, footer = l.strip().split('|', 1)
                    footer_map[page] = footer
                except ValueError:
                    pass

        for fn in os.listdir(dir_):
            if header_map.has_key(fn):
                header = header_map[fn]
                match = False
            else:
                match = True
                header = 'Not important'
            lines = []
            with codecs.open('{}/{}'.format(dir_, fn), mode='rb', encoding='utf-8') as f:
                for l in f:
                    line = l.strip()
                    if match and line != footer_map[fn]:
                        lines.append(line)
                    elif line == header:
                        match = True
            if lines:
                with codecs.open('{}/{}'.format(dir_, fn), mode='wb', encoding='utf-8') as f:
                    for line in lines:
                        f.write(u'{}\n'.format(line))
            else:
                raise Exception('File {} does not have its header'.format(fn))


    def make_possible_proper_name_doc(self, dir_):
        proper_nouns = Counter()
        hold_word = ''
        for fn in os.listdir(dir_):
            if fn.endswith('.txt'):
                with codecs.open('{}/{}'.format(dir_, fn), mode='r', encoding='utf-8') as f:
                    for l in f:
                        words = l.split()
                        if len(words): # ignore blank lines
                            for word in words:
                                if self.spell_checker.proper_noun(hold_word, word):
                                    proper_nouns[self.letters(word)] += 1
                                hold_word = word
        with codecs.open('{}/possible_proper_nouns.txt'.format(self.output_dir), mode='wb', encoding='utf-8') as f:
            for proper_noun, count in sorted(proper_nouns.items(), key=lambda x: x[0]):
                if count > 2:
                    f.write(u'{}\n'.format(proper_noun))

    def make_word_fix_doc(self, dir_):
        checker = self.spell_checker
        bad_words = set()

	bad_bad_map = {}
        word_set = set()
        for fn in os.listdir(dir_):
            if fn.endswith('.txt'):
                with codecs.open('{}/{}'.format(dir_, fn), mode='rb', encoding='utf-8') as f:
                    for l in f:
                        word_set.update(l.split())
	print '{} words'.format(len(word_set))
 
        words = list(word_set)
        for idx, bad_word_key in enumerate(self.spell_checker.failed_words(words)):
            if bad_word_key:
                bad_word = words[idx]
                bad_words.add(spell_checker._decode(bad_word))
                bad_bad_map[words[idx]] = bad_word
	print '{} bad words'.format(len(bad_words))

        fixes = self.fixed_words(bad_words)
	print '{} fixes'.format(len(fixes))
	still_bad = Counter()
        solos = []
        multis = []
        for bad_version, bad_word in sorted(bad_bad_map.items(), key=lambda x: x[0]):
            try:
                good_versions = fixes[bad_word]
                # remove hyphened versions if others are present
                if not '-' in bad_word:
                    good_unhyphened = [word for word in good_versions if not '-' in word]
                    if good_unhyphened:
                        good_versions = good_unhyphened
                fixed_good_versions = []
                for version in good_versions:
                    fixed_good_versions.append(bad_version.replace(bad_word, version))
                if len(fixed_good_versions) > 1:
                    multis.append((bad_version, fixed_good_versions,))
                elif fixed_good_versions:
                    solos.append((bad_version, fixed_good_versions,))
            except KeyError:
                still_bad[bad_word] += 1
        with codecs.open('{}/word_fixes.txt'.format(self.output_dir), mode='wb', encoding='utf-8') as f:
            for bad_version, fixed_good_versions in multis:
                f.write(u'{}|{}\n'.format(bad_version, self.delimiter.join(fixed_good_versions)))
            for bad_version, fixed_good_versions in solos:
                f.write(u'{}|{}\n'.format(bad_version, self.delimiter.join(fixed_good_versions)))
        with codecs.open('{}/bad_words.txt'.format(self.output_dir), mode='wb', encoding='utf-8') as f:
            for bad_word, cnt in still_bad.most_common():
                f.write(u'{:>20}: {:>3}\n'.format(bad_word, cnt))

    def file_sort(self, filename):
        basename, ext = os.path.splitext(filename)
        try:
            return int(basename)
        except ValueError:
            return -1
    def make_line_join_doc(self, dir_):
        """Creates a document of fixes for cross-line joining.
        Uses all the documents found in dir_
        Writes to 'hyphen_fixes' in current directory
        with the format:
        joinedwords|delimiter-separated-fixes
        """
        checker = self.spell_checker
        potential_fix_list = []
        fixes = set()
        hold_word = ''
        for fn in sorted(os.listdir(dir_), key=self.file_sort):
            if fn.endswith('.txt'):
                sys.stdout.write('.')
                with codecs.open('{}/{}'.format(dir_, fn), mode='r', encoding='utf-8') as f:
                    for l in f:
                        words = l.split()
                        if words: # ignore blank lines
                            joinables = spell_checker.valid_joinables(hold_word, words[0], self.spell_checker)
                            for joinable in joinables:
                                potential_fix_list.append(PotentialLineBreakFix(hold_word, words[0], joinable, False))
                            fixes.update(joinables)
                            # blank out the hold word if only one word in line
                            if len(words) > 1:
                                hold_word = words[-1]
                            else:
                                hold_word = ''
        print ''
        print '{} potential fixes'.format(len(potential_fix_list))
        print '{} joinables'.format(len(fixes))

        # need this to maintain order when checking
        fixes_array = list(fixes)
        good_changes = {}
        good_versions, bad_words = checker.good_and_bad(fixes_array)
        print '{} good versions'.format(len(good_versions))
        # Easy fixes: the join is already spelled correctly, so call it good
        for w in good_versions:
            for idx, fix in enumerate(potential_fix_list):
                if fix.joinable == w:
                    good_changes[fix.key] = [w,]
                    fix.fixed = True 

        # try to fix all the joins that might also be misspelled
        for bad_word, good_change_set in self.fixed_words(bad_words).items():
            for idx, fix in enumerate(potential_fix_list):
                if fix.joinable == bad_word:
                    good_changes[fix.key] = good_change_set
                    fix.fixed = True 
        print '{} bad versions fixed'.format(len(good_changes) - len(good_versions))

        # join the words if the first word ends in hyphen anyway
        for fix in potential_fix_list:
            if not fix.fixed and ends_with_hyphen(fix.first_word):
                good_changes[fix.key] = [u'{}{}'.format(fix.first_word, fix.second_word),]

        with codecs.open('{}/line_join_fixes.txt'.format(self.output_dir), mode='wb', encoding='utf-8') as f:
            for bad_word, good_versions in good_changes.items():
                    f.write(u'{}|{}\n'.format(bad_word, '|'.join(good_versions)))

    def fixed_words(self, bad_words):
        """ Takes a list of bad words and returns a dictionary of the
        bad words with 1 or more fixes.
        """
        checker = self.spell_checker
        good_changes = {}
        for bad_word in bad_words:
            changed_versions = checker.transformed_variations(bad_word)
            good_versions = []
            if changed_versions:
                changed_words = [t[0] for t in changed_versions]
		good_versions, wtvr = checker.good_and_bad(changed_words)
                if good_versions:
                    good_changes[bad_word] = good_versions

        return good_changes

    def page_image_info(self, text_dir_, images_dir_):
        with open('working/page_info.csv', 'wb') as f:
            writer = csv.writer(f)

            for fn in os.listdir(text_dir_):
                print fn
                name, extension = os.path.splitext(fn)
                text_path = '{}/{}.txt'.format(text_dir_, name)
                image_path = '{}/{}.pbm'.format(images_dir_, name)
                if extension == '.txt' and os.path.exists(image_path):
                    print 'in'    
                    sys.stdout.write('.')
                    pi = PageInfo(image_path, text_path)
                    page_lines = pi.line_guess()
                    for line in page_lines:
                        writer.writerow((
                            name,
                            line.height,
                            line.left_margin,
                            line.y,
                            line.width,))


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
                if current_line.height > minimum_height:
                    lines.append(current_line)
                current_line = LineInfo(idx)
            current_line.add_pixel_line(pixel_line)
        return lines

    def line_guess_test(self, header_offset=0):
        text_idx = 0
        dipped = False
        lines = []
        for idx, pixel_line in enumerate(self.pixel_lines):

            if pixel_line.density/float(len(self.lines[text_idx])) > .03:
                lines.append(LineInfo(idx))
        return lines

    def initial_min_height(self, adjusting_factor=.5):
        block = 0.0
        for idx, pixel_line in enumerate(self.pixel_lines):
            if not pixel_line.blank:
                block += 1
        return (block * adjusting_factor)/len(self.lines)

    def line_guess(self, header_offset=0):
        """ Tries to guess where the lines of text in the image are.

        header_offset: if there is gunk at the beginning
        you don't want to count."""
        lines = []
        if not self.lines:
            return lines
        minimum_jump = self.width
        minimum_height = self.initial_min_height()
        best_lines = []
        while len(best_lines) != len(self.lines) and 0 < minimum_jump:
            lines = self.chop_by_leap_forward(minimum_jump, minimum_height, header_offset)
            if abs(len(lines) - len(self.lines)) < abs(len(best_lines) - len(self.lines)):
                best_lines = lines
            # minimum height is 80% of average
            minimum_height = sum([line.height for line in lines])/(len(self.lines)*2)
            minimum_jump -= 10
        return best_lines

    def margin_version(self, output_file_name):
        im = Image.open(self.path_to_image)
        d = ImageDraw.Draw(im)
        width, height = im.size
        for idx, pixel_line in enumerate(self.pixel_lines):
            d.line((0, idx, pixel_line.left_margin, idx,))
        im.save(output_file_name)

    def grid_version(self, output_file_name):
        im = Image.open(self.path_to_image)
        d = ImageDraw.Draw(im)
        width, height = im.size
        for idx, line in enumerate(self.line_guess()):
            d.line((0, line.y, width, line.y,))
        im.save(output_file_name)

    def chopped_version(self, output_file_path, header_offset=0):
        """ Outputs one file per line.

        output_file_path should have a {} to hold
        the line index.
        """
        im = Image.open(self.path_to_image)
        width, height = im.size
        for idx, line in enumerate(self.line_guess(header_offset)):
            line_image = line.image(im)
            line_image.save(output_file_path.format(idx))

class LineInfo(object):
    def __init__(self, y):
	self.pixel_lines = []
        self.height = 0
        self.left_margin = None
        self.y = y
        self.width = None

    def add_pixel_line(self, pixel_line):
	self.pixel_lines.append(pixel_line)
        self.height += 1
        if self.left_margin:
            self.left_margin = min(self.left_margin, pixel_line.left_margin)
        else:
            self.left_margin = pixel_line.left_margin
        if not self.width:
            self.width = pixel_line.full_length
        return True

    def density(self):
        return sum([pl.density for pl in self.pixel_lines])/(len(self.pixel_lines or 1))

    def image(self, image, buffer_=0, top=-1, bottom=None):
        """ Returns slice of image associated with this line.

        parameters:
        image - Image object of the page
        buffer = multiple of line height to include
        """
            
        width, height = image.size
        if top < 0 or not bottom:
            top = max(0, self.y - (buffer_*self.height))
            bottom = min(height, self.y + self.height + (buffer_*self.height))
        
        return image.crop((0, top, width, bottom))
        
    def __str__(self):
        return '{}, {}, {}, {}'.format(
                            self.height,
                            self.left_margin,
                            self.y,
                            self.width)


class PixelLineInfo(object):
    """ Information about a given line of pixels."""
    def __init__(self, data):
	if 255 in data:
	    self.threshold = data.index(255)
        else:
            self.threshold = 0
        if 0 in data[self.threshold:]:
            self.left_margin = data[self.threshold:].index(0) + self.threshold
            self.blank = False
        else:
            self.left_margin = len(data)
            self.blank = True
        self.full_length = len(data[self.left_margin:])
        if self.blank:
            self.density = 0
        else:
            self.density = float(data.count(0))/self.full_length

class PotentialLineBreakFix(object):
    def __init__(self, first_word, second_word, joinable, fixed):
        self.first_word = first_word
        self.second_word = second_word
        self.joinable = joinable
        self.fixed = fixed
        self.key = u'{}_{}'.format(first_word, second_word)
    def __str__(self):
        return u' '.join([self.key, self.joinable, str(self.fixed),])
