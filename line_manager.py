#!/usr/bin/env python
""" This module handles all of the management of lines in a scanned book."""

from collections import Counter, defaultdict
import codecs
import os
import re
import sys

from regex_helper import REGEX_LETTER, REGEX_CAPITAL, REGEX_SMALL

# matching functions
has_digit = re.compile('\d', re.UNICODE).search
begins_with_lowercase = re.compile(u'^{}'.format(REGEX_SMALL), re.UNICODE).match
ends_with_hypen = re.compile(r'.*-$', re.UNICODE).match
# LAST_FIXED_PAGE = 191
LAST_FIXED_PAGE = 133

HTML_HEADER = """
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN"
  "http://www.w3.org/TR/html4/strict.dtd">		 
<html>
  <head>
  <meta http-equiv="content-type" content="text/html; charset=UTF-8">
  <title>{}</title>
  </head>
<body>
<p>{}</p>
<p>{}</p>
"""
class LineManager(object):
    """ Utility class for managing line objects."""
    def __init__(self, spell_checker, start_page=0, end_page=0):
        self.page_numbers = []
        self.pages = {}
        self.average_length = 0
        self.spell_checker = spell_checker
        self.start_page = start_page
        self.end_page = end_page

    def remove_headers(self, header):
        """ Goes through the first rows until it finds
        either a header or a valid-looking line.

        Marks header lines as invalid."""
	pairs = []
	header_words = header.split()
        for page_nbr, page in self.pages.items():
            if not re.match(r'\d+$', page[0].text):
                page[0].valid = False
            continue
            no_header = True
            i = 0
            while no_header:
		try:
                    text_words = page[i].text.split()
                except IndexError:
                    break
		match_count = 0
                if len(page[i].text) >= len(header):
                    no_header = False
                    for word in text_words:
                        if word in header_words:
                            match_count += 1
                    if len(header_words) < len(text_words) + 3 and \
                        match_count > 1:
                        for j in xrange(i + 1):
                            page[j].valid = False
                else:
                    i += 1

    def load(self, raw_file_dir):
        """ Creates lines out of all the lines in a directory."""
        for fn in sorted(os.listdir(raw_file_dir), key=lambda x: int(os.path.splitext(x)[0])):
            
	    basename, ext = os.path.splitext(fn)
            if int(basename) < self.start_page or ext != '.txt':
                continue

            if self.end_page > 0 and int(basename) > self.end_page:
                break
            with codecs.open('{}/{}'.format(raw_file_dir, fn), mode='r', encoding='utf-8') as f:
                print 'Loading page {:>3}'.format(basename)
                self.pages[basename] = []
                idx = 1
                for l in f:
                    line = Line(l.strip(), idx, self.spell_checker)
                    self.pages[basename].append(line)
                    idx += 1
        self.average_length = self.calculate_average_length()
        self.page_numbers = sorted(self.pages.keys(), key=lambda x: int(x))

    def calculate_average_length(self):
        """ Returns the average length (int) of all valid lines."""
        total = 0
        line_count = 0
        for page in self.pages.values():
            for line in page:
                line_length = len(line.text)
                if line.valid:
                    total += line_length
                    line_count += 1
        try:
            return total/line_count
        except ZeroDivisionError:
            return 0

    def interactive_fix(self):
        replaceable = (re.compile(u'({}+)["\u00B0]+({}+)'.format(REGEX_LETTER, REGEX_LETTER), flags=re.UNICODE), r"\1'\2")
        page_viewed = False
        for page_nbr in self.page_numbers:
            if int(page_nbr) < self.start_page:
                continue
            lines = self.pages[page_nbr]
            for idx, line in enumerate(lines):
                to_check = line.should_check()
                if to_check:
                    if not page_viewed:
                        os.system('gnome-open images/pages/{}.pbm'.format(page_nbr))
                        page_viewed = True
                    print '\n\n\n\n\n'
                    print 'Something odd on page {} line {}'.format(page_nbr, line.line_nbr)
                    try:
                        print u'*** {}'.format(lines[idx-1].text)
                    except IndexError:
                        pass
                    print line.text
                    try:
                        print u'*** {}'.format(lines[idx+1].text)
                    except IndexError:
                        pass
                    print u' | '.join([w.text for w in to_check])
                    sys.stdout.write('(m)ark, (i)gnore, (q)uit >')
                    action = raw_input()
                    if action.startswith('q'):
                        self.end_page = page_nbr
                        return
                    elif action.startswith('m'):
                        fix = raw_input()
                        if fix:
                            line.manual_fix = fix
                        else:
                            line.manual_fix = '(no text)'
                    elif not action.startswith('i'):
                        for word in to_check:
                            print '\n\n'
                            print word.text
                            if word.misspelled:
                                replacement = raw_input()
                                if replacement:
                                    if replacement == 'atd':
                                        self.spell_checker.add_word(word.text)
                                    else:
                                        word.text = replacement.decode('utf-8')
                                        word.misspelled = False
                            elif word.odd_punctuation:
                                replace = True
				m = replaceable[0].search(word.text)
                                if m:
                                    sys.stdout.write('(e)dit or (r)eplace with apostrophe >')
                                    decision = raw_input()
                                    if not decision.startswith('e'):
                                        replace = False
                                    if decision.startswith('r'):
                                        word.text = replaceable[0].sub(replaceable[1], word.text)
                                if replace:
                                    replacement = raw_input()
                                    if replacement:
                                        word.text = replacement.decode('utf-8')
                                        word.misspelled = False
                            elif word.hyphenated:
                                sys.stdout.write('(a)dd space, (j)oin words, (e)dit, (r)eplace hyphen >')
                                replacement = raw_input()
                                if replacement == 'a':
                                    word.text = word.text.replace('-', ' - ').strip()
                                elif replacement == 'j':
                                    word.text = re.sub(' *- *', '', word.text)
                                elif replacement == 'r':
                                    replacement_2 = raw_input()
                                    if replacement_2:
                                        word.text = word.text.replace('-', replacement_2)
                                elif replacement == 'e':
                                    replacement = raw_input()
                                    if replacement:
                                        word.text = replacement.decode('utf-8')
                    line.rebuild()

    def write_html(self, book_config):
	self.calculate_average_length()
        html_file_name = book_config.get('metadata', 'html_file')
        title = book_config.get('metadata', 'title')
        author = book_config.get('metadata', 'author')
        non_letter = re.compile('\W$', flags=re.UNICODE)
        with codecs.open(html_file_name, mode='w', encoding='utf-8') as f:
            f.write(HTML_HEADER.format(title, title, author))
            last_line_short = False
            for page_nbr in self.page_numbers:
                print 'Writing page {:3}'.format(page_nbr)
                f.write('<!-- Page {} -->\n'.format(page_nbr))
                for line in self.pages[page_nbr]:
                    
                    this_line_short = self.average_length > len(line.text) and bool(non_letter.search(line.text))
                    if last_line_short: # and this_line_short:
                        f.write('<p>\n')
                    last_line_short = this_line_short
                    """
                    if self.spell_checker.check_line(line.text):
                        f.write('<!-- Spelling Errors: line {} -->\n'.format(line.line_nbr))
                    if line.has_odd_punctuation():
                        f.write('<!-- Odd Punctuation: line {} -->\n'.format(line.line_nbr))
                    """
                    f.write(line.text)
                    f.write('\n')

    def write_pages(self, clean_file_dir, fix=True):
        try:
            os.makedirs(clean_file_dir)
        except OSError:
            pass
        if fix:
            self.fix_lines()
        for page_nbr in self.page_numbers:
            if int(page_nbr) < self.start_page:
                continue
            if self.end_page and int(page_nbr) > self.end_page:
                return
            print 'writing page {}'.format(page_nbr)
            with codecs.open('{}/{}.txt'.format(clean_file_dir, page_nbr), mode='w', encoding='utf-8') as f:
                for line in self.pages[page_nbr]:
                    if line.valid:
                        if line.manual_fix:
                            f.write('# FIX ME {}\n'.format(line.manual_fix))
                        f.write(line.text)
                        f.write('\n')

    def fix_line(self, line):
        sm = SubstitutionManager(self.spell_checker)
        if line.valid:
            line.text = sm.update_single_characters(line.text)
            line.text = sm.update_numbers(line.text)
            line.text = sm.update_words(line.text)

    def fix_lines(self):
        last_line = None
        for page_nbr in self.page_numbers:
            if int(page_nbr) < self.start_page:
                continue
            if self.end_page and int(page_nbr) > self.end_page:
                print page_nbr, self.end_page
                return
            print 'fixing page {:>3}'.format(page_nbr)
            for line in self.pages[page_nbr]:
                if line.valid:
                    self.fix_hyphen((last_line, line,))
                    line.fix()
                    if line.text.strip():
                        last_line = line

    def quick_fix(self):
        """ Replaces all the must-replace characters."""
        for page_nbr in self.page_numbers:
            for line in self.pages[page_nbr]:
                if line.valid:
                    line.build_words(True)

    def fix_hyphen(self, lines):
        if not lines[0] or not lines[1]:
            return
        lines[1].first_word().prepend(lines[0].last_word())
        lines[0].rebuild()
        lines[1].rebuild()

class Line(object):
    """ Manages individual lines of a book. """
    def __init__(self, raw_text, line_nbr, spell_checker):
        self.raw_text = raw_text
        self.text = raw_text
        self.line_nbr = line_nbr
        self.valid = True
        self.null_word = Word('', spell_checker, True)
        self.spell_checker = spell_checker
	self.words = []
        self._built = False
        self.manual_fix = False

    def should_check(self):
        """ Returns a list of words that should be checked."""
        self.build_words()
        to_check = []
        for word in self.words:
            if word.misspelled or word.odd_punctuation:
                to_check.append(word)
            # Don't add if just a hyphen alone
            elif False and word.hyphenated and len(word.text) > 1:
                to_check.append(word)
        return to_check

    def rebuild(self):
        self.build_words()
        self.text = ' '.join([w.text for w in self.words if w.text])

    def build_words(self, skip_spell_check=False):
        if self._built:
            return
        
        already_spell_checked = skip_spell_check or not self.spell_checker.check_line(self.text)
	for w in self.text.split():
            self.words.append(Word(w, self.spell_checker, already_spell_checked))
        self._built = True
        self.rebuild()

    def last_word(self):
        self.build_words()
        try:
            return [word for word in self.words if word.text][-1]
        except IndexError:
            return self.null_word

    def first_word(self):
        self.build_words()
        try:
            return [word for word in self.words if word.text][0]

        except IndexError:
            return self.null_word

    def fix(self):
        self.build_words()
        for word in self.words:
            word.correct_spelling()
            word.hyphenate()
        self.rebuild()       

    def pop_last_word(self):
        """ For joining hyphens, removes last word of line."""
        popped = self.last_word().replace(r'(', r'\(')
        self.text = re.sub(u'{}$'.format(popped), '', self.text, flags=re.UNICODE).strip()


    def prepend_word(self, word):
        """ For joining hyphens, puts the prefix of the word in front."""
        self.text = u'{}{}'.format(word, self.text)

    def has_odd_punctuation(self):
        """ Returns a boolean if matches any bad punctuation."""
        for w in self.text.split():
            word = Word(w, self.spell_checker)
            if word.odd_punctuation:
                return True
        return False  

class SubstitutionManager(object):
    """ Manages the substitutions of characters."""
    def __init__(self, spell_checker):
        self.spell_checker=spell_checker

    def update_single_characters(self, line):
        """ Returns a line in which known undesirable
        single-characters have been replaced."""
        words = []
        for w in line.split():
            # creating has the side effect of quick fix
            words.append(Word(w, self.spell_checker))
        return ' '.join([w.text for w in words if w.text])


    def update_words(self, line):
        """ Look for misspelled words and replace with correctly-spelled
        words if possible."""
        words = []
        for w in line.split():
            word = Word(w, self.spell_checker)
            word.correct_spelling()
            word.hyphenate()
            words.append(word)
        return ' '.join([w.text for w in words if w.text])

    def update_numbers(self, line):
        """ Replaces numbers with letters and makes sure
        they become real words."""
        return self.update_words(line)

class Word(object):
    """ Actually, the holder of a space-separated chunk of text."""
    def __init__(self, raw_text, spell_checker, already_spell_checked=False):
        self.raw_text = raw_text
        self.text = raw_text
        self.spell_checker = spell_checker
        self.checked = False
        self.quick_fix()
        self.verify(already_spell_checked)

    def quick_fix(self):
        """
        Replaces characters that always need to be replaced.
        """
	self.text = self.spell_checker.quick_fix(self.text)

    def verify(self, already_spell_checked):
        """ Sets flags for
        * misspelled
        * odd punctuation
        * hyphenation
        """
        if already_spell_checked:
            self.misspelled = False
        else:
            self.misspelled = bool(self.spell_checker.check_line(self.text))
        self.odd_punctuation = self.spell_checker.odd_punctuation(self.text)
        self.hyphenated = '-' in self.text
        self.checked = True

    def correct_spelling(self):
        """ Tries to remove the misspell flag """
        if self.misspelled: 
            new_word = self.spell_checker.fix_spelling(self.text)
            if new_word != self.text:
                # Fixed!
                self.text = new_word
                self.misspelled = False        
		self.odd_punctuation = self.spell_checker.odd_punctuation(self.text) 
        
    def hyphenate(self):
        """ Tries to correct spelling by hyphenating self.
        Does not hyphenate words that already have a hyphen.
	"""
        if self.misspelled and not self.hyphenated:
            new_word = self.spell_checker.hyphenate(self.text)
            if new_word != self.text:
                # Fixed!
                self.text = new_word
                self.hyphenated = True
                self.misspelled = False        
		self.odd_punctuation = self.spell_checker.odd_punctuation(self.text) 

    def prepend(self, word):
        """ Takes another word object and prepends its text
         
        If it prepends, it will 'blank out' the text of the
        other word.

        Parameters:
        word: another Word object

        Rules:
        If the text of this word is a lower case letter
        AND
        Both words are spelled correctly
        AND
        the parameter word is hyphenated
        THEN
        it will join the two as a hyphenate

        IF
        the text of this word is lower case
        AND
        One of the words is misspelled
        AND
        Bringing the words together creates a valid word            
        OR
        Bringing the parameter word[:-1] and self
        together creates a valid word
        THEN
        it will join the two
	"""
        if not begins_with_lowercase(self.text):
            return

        if self.misspelled or word.misspelled:
            # try adding the words directly
            new_word = word.text + self.text
            if not self.spell_checker.check_line(new_word):
                self.spell_checker.log_fix('cross_line_fix', 'join_all',
                    u'{} {}'.format(word.text, self.text), new_word)
                self.mispelled = False
                word.mispelled = False
                self.text = new_word
                word.text = ''
                return
            # try removing the last character
            new_word = word.text[:-1] + self.text
            if not self.spell_checker.check_line(new_word):
                self.spell_checker.log_fix('cross_line_fix', 'join_truncated',
                    u'{} {}'.format(word.text, self.text), new_word)
                self.mispelled = False
                word.mispelled = False
                self.text = new_word
                word.text = ''
                return

        elif ends_with_hypen(word.text):
            self.hyphenated = True
            word.hyphenated = False
            self.text = word.text + self.text
            word.text = ''

if __name__ == '__main__':
    lm = LineManager(None)
    lm.load('.')
    lm.remove_headers('THUS WAS ADONIS MURDERED')
    odd_punctuation = defaultdict(Counter)
    for page_nbr in lm.page_numbers:
        for line in lm.pages[page_nbr]:
            for k, l in line.odd_punctuation().items():
                for item in l:
                    odd_punctuation[k][item] += 1
    for k, l in odd_punctuation.items():
        print k
        for item, cnt in l.most_common():
            print '   {:3>}: {}'.format(cnt, item)
