#!/usr/bin/env python
""" Contains classes that implement a spell-checking interface:
* given a string, return the mis-spelled words
* given a string, return whether it is 'garbage'
"""

import codecs
import re
from subprocess import Popen, PIPE

from regex_helper import REGEX_LETTER, REGEX_CAPITAL, REGEX_SMALL

class BaseSpellFixer(object):
    """
    Class that holds regexes for all languages.
    """
    def __init__(self):
        """ Sets the following arrays:

        quick_fixes: regexes that should *always* be done
        letter_fixes: regexes to swap character(s) to correct misspelling
        
        Implementing subclasses should add their own
        fixes to these arrays.
        """
        self.quick_fixes = [
            # hyphen at end of line
            (re.compile(u'(.)[=<~\xbb\u2014\u2013]+$', flags=re.UNICODE), r'\1-', 'hyphen-at-end-of-line',),
            # hyphen between letters
            (re.compile(u'({})[=<~\u2014\u2013\xbb]+({})'.format(REGEX_SMALL, REGEX_SMALL), flags=re.UNICODE), r'\1-\2', 'hyphen-between-letters',),
            # hyphen anywhere
            (re.compile(u'[~\u2014\u2013\xbb]+', flags=re.UNICODE), '-', 'hyphen-anywhere',),
            # weird combined f
            (re.compile(u'\ufb01', flags=re.UNICODE), 'fi', 'weird-fi',),
            (re.compile(u'\ufb02', flags=re.UNICODE), 'fl', 'weird-fl',),
            # smart quotes and accents to dumb quotes
            (re.compile(u'[\u2019\u2018\u0060\u00B4]', flags=re.UNICODE), "'", 'smart-to-single-quote',),
            (re.compile(u'[\u201c\u201d]', flags=re.UNICODE), '"', 'smart-to-double-quote',),
            (re.compile(u'_?]({}+)'.format(REGEX_SMALL), flags=re.UNICODE), r'J\1', 'to-J',),
            # I-I or I-l to H
            (re.compile(u'I-[Il]({}+)'.format(REGEX_SMALL), flags=re.UNICODE), r'H\1', 'to-H',),
        ]
        self.letter_fixes = [
            (re.compile(r'rn', flags=re.UNICODE), r'm', u'rn-to-m',),
            (re.compile(r'm', flags=re.UNICODE), r'rn', u'm-to-rn',),
            (re.compile(u'({})O'.format(REGEX_LETTER), flags=re.UNICODE), r'\1o', u'XO-to-Xo',),
            (re.compile(r'ck', flags=re.UNICODE), u'd', u'ck-to-d',),
            (re.compile(r'cl', flags=re.UNICODE), u'd', u'cl-to-d',),
            (re.compile(r'lll\b', flags=re.UNICODE), u"'ll", u'lll-to-\'ll',),
            (re.compile(r'\bVV', flags=re.UNICODE), u'W', u'VV-to-W',),
            (re.compile(u'({})({})\\B'.format(REGEX_SMALL, REGEX_CAPITAL), flags=re.UNICODE), r'\1 \2', u'xX-to-x[space]X',),
            (re.compile(r'\Be\B', flags=re.UNICODE), u'c', u'e-to-c',),
            (re.compile(u'\u00F1', flags=re.UNICODE), u'fi', u'n-tilde-to-fi',),
            (re.compile('1', flags=re.UNICODE), u'l', u'1-to-l',),
            (re.compile('1', flags=re.UNICODE), u'i', u'1-to-i',),
            (re.compile('0', flags=re.UNICODE), u'o', u'0-to-o',),
            (re.compile('5', flags=re.UNICODE), u's', u'5-to-s',),
            (re.compile(u'\\boo({}{{3,}})'.format(REGEX_SMALL), flags=re.UNICODE), r'co\1', 'oo-to-co',),
        ]
	# things that need punctuation and therefore cannot be batched
	self.punctuation_fixes = [

	]
        self.odd_punctuation = [
            # begin paragraph directly after a letter
            re.compile(u'{}+\\('.format(REGEX_LETTER), flags=re.UNICODE),
            # ending punctuation inside a word
            re.compile(u'[{}]+{}+'.format(re.escape('?)!,.:;'), REGEX_LETTER), flags=re.UNICODE),
            # quotation mark or degree sign inside a word
            re.compile(u'{}+["\u00B0]+{}+'.format(REGEX_LETTER, REGEX_LETTER), flags=re.UNICODE),
            # strange thing in front of or behind a letter
            re.compile(u'{}[{}]+'.format(REGEX_LETTER, re.escape('_/<=>%[\]{|}')), flags=re.UNICODE),
            re.compile(u'[{}]+{}'.format(re.escape('_/<=>%[\]{|}'), REGEX_LETTER), flags=re.UNICODE),
            # number-letter combinations
            re.compile(u'\\d{}'.format(REGEX_LETTER), flags=re.UNICODE),
            re.compile(u'{}\\d'.format(REGEX_LETTER), flags=re.UNICODE),
        ]
class EnglishSpellFixer(BaseSpellFixer):
    def __init__(self):
        super(EnglishSpellFixer, self).__init__()
        self.quick_fixes.extend([
            (re.compile(r'\bl\b', flags=re.UNICODE), u'I', u'l-to-I',),
            (re.compile(r'mg\b', flags=re.UNICODE), u'ing', u'mg-to-ing',),
            (re.compile(r'\b([Ww])n', flags=re.UNICODE), r'\1h', u'Wwn-to-Wwh',),
            (re.compile(r'\bIld\b', flags=re.UNICODE), u"I'd", u'Ild-to-I\'d',),
            (re.compile(r'\b([DdSsTtNn])0(\W|$)', flags=re.UNICODE), r'\1o\2', u'X0-to-Xo',),
        ])
        self.letter_fixes.extend([
            (re.compile(u'({}{}+)s'.format(REGEX_CAPITAL, REGEX_SMALL), flags=re.UNICODE), r"\1's", u'make possessive',),
            (re.compile(u'({})[il]([st])\\b'.format(REGEX_SMALL), flags=re.UNICODE), r"\1'\2", u'add-apostrophe',),
            (re.compile(u'\\bof({}{{3,}})'.format(REGEX_SMALL), flags=re.UNICODE), r'of \1', u'ofxxx-to-of[space]xxx',),
        ])

class FrenchSpellFixer(BaseSpellFixer):
    def __init__(self):
        super(FrenchSpellFixer, self).__init__()
        self.quick_fixes.extend([
            (re.compile(r'\b([Cc])est\b', flags=re.UNICODE), r"\1'est", "Ccest-to-Cc'est",),
            (re.compile(r'\bll\b', flags=re.UNICODE), r"Il", u'll-to-Il',),
            (re.compile(u'({}+)["\u00B0]+({}+)'.format(REGEX_LETTER, REGEX_LETTER), flags=re.UNICODE),
                r'\1-\2', u'x"x-to-x\'x',),
            (re.compile(r'\bel\b', flags=re.UNICODE), u'et', 'el-to-et',),
        ])
        self.letter_fixes.extend([
            # replace c with cedilla
            (re.compile(r'c', flags=re.UNICODE), u'\u00E7', u'c-to-\u00E7',),
            # replace a with a accent acute
            (re.compile(u'[a\u00E3\u00E4\u00E5\u00E0\u00E2]', flags=re.UNICODE), u'\u00E1', u'a-to-\u00E1',),
            # replace a with a accent grave
            (re.compile(u'[a\u00E3\u00E4\u00E5\u00E1\u00E2]', flags=re.UNICODE), u'\u00E0', u'a-to-\u00E0',),
            # replace a with a circumflex
            (re.compile(u'[a\u00E3\u00E4\u00E5\u00E0\u00E1]', flags=re.UNICODE), u'\u00E2', u'a-to-\u00E2',),
            # replace e with e accent acute
            (re.compile(u'[e\u00EB\u00E8\u00EA]', flags=re.UNICODE), u'\u00E9', u'e-to-\u00E9',),
            # replace e with e accent grave
            (re.compile(u'[e\u00EB\u00E9\u00EA]', flags=re.UNICODE), u'\u00E8', u'e-to-\u00E8',),
            # replace e with e circumflex
            (re.compile(u'[e\u00EB\u00E8\u00E9]', flags=re.UNICODE), u'\u00EA', u'e-to-\u00EA',),
            # replace accented i with plain i
            (re.compile(u'[\u00EF\u00ED\u00EC\u00EE]', flags=re.UNICODE), u'i', u'odd-i-to-i',),
            # replace i with i accent acute
            (re.compile(u'[i\u00EF\u00EC\u00EE]', flags=re.UNICODE), u'\u00ED', u'i-to-\u00ED',),
            # replace i with i accent grave
            (re.compile(u'[i\u00EF\u00ED\u00EE]', flags=re.UNICODE), u'\u00EC', u'i-to-\u00EC',),
            # replace i with i circumflex
            (re.compile(u'[i\u00EF\u00EC\u00ED]', flags=re.UNICODE), u'\u00EE', u'i-to-\u00EE',),
            # replace o with o accent acute
            (re.compile(u'[o\u00F7\u00F6\u00F5\u00F2\u00F4]', flags=re.UNICODE), u'\u00F3', u'o-to-\u00F3',),
            # replace o with o accent grave
            (re.compile(u'[o\u00F7\u00F6\u00F5\u00F3\u00F4]', flags=re.UNICODE), u'\u00F2', u'o-to-\u00F2',),
            # replace o with o circumflex
            (re.compile(u'[o\u00F7\u00F6\u00F5\u00F2\u00F3]', flags=re.UNICODE), u'\u00F4', u'o-to-\u00F4',),
            # replace u with u accent acute
            (re.compile(u'[u\u00FC\u00F9\u00FB]', flags=re.UNICODE), u'\u00FA', u'u-to-\u00FA',),
            # replace u with u accent grave
            (re.compile(u'[u\u00FC\u00FA\u00FB]', flags=re.UNICODE), u'\u00F9', u'u-to-\u00F9',),
            # replace u with u circumflex
            (re.compile(u'[u\u00FC\u00F9\u00FA]', flags=re.UNICODE), u'\u00FB', u'u-to-\u00FB',),
            # replace starts-with-dot-P with J'
            (re.compile(u'\\.P({}{{3,}})'.format(REGEX_SMALL), flags=re.UNICODE), r"J'\1", u'.Px-to-J\'x',),
            # replace starts-with-P with l'
            (re.compile(u'\\bP({}{{3,}})'.format(REGEX_SMALL), flags=re.UNICODE), r"l'\1", u'Px-to-l\'x',),
            # replace starts-with-dot-F with J'
            (re.compile(u'\\.F({}{{3,}})'.format(REGEX_SMALL), flags=re.UNICODE), r"J'\1", u'.Fx-to-J\'x',),
            # replace starts-with-F with l'
            (re.compile(u'\\bF({}{{3,}})'.format(REGEX_SMALL), flags=re.UNICODE), r"l'\1", u'Fx-to-l\'x',),
            # replace starts-with-Y with l'
            (re.compile(u'\\bY({}{{3,}})'.format(REGEX_SMALL), flags=re.UNICODE), r"l'\1", u'Yx-to-l\'x',),
            # replace - with '
            (re.compile(u'({})-({})'.format(REGEX_LETTER, REGEX_SMALL), flags=re.UNICODE), r"\1'\2", u"hyphen-to-apostrophe",),
            # replace Cce with Cc'e accent acute
            (re.compile(u'([Cc])[e\u00E8\u00E9\u00EA\u00EB]', flags=re.UNICODE), u"\\1'\u00E9", u'Ce-to-C\'\u00E9',),
            # replace Cce with Cc'e
            (re.compile(u'([Cc])[e\u00E8\u00E9\u00EA\u00EB]', flags=re.UNICODE), r"\1'e", u'Ce-to-C\'e',),
            # replace rf with n'
            (re.compile(u'rf({}{{2,}})'.format(REGEX_SMALL), flags=re.UNICODE), r"n'\1", u'rf-to-n\'',),
            # replace x i-diaeresis with x'i
            (re.compile(u'\\b([dlns])\u00EF', flags=re.UNICODE), r"\1'i", u'x-i-diaeresis-to-x\'i',),
        ])

	self.punctuation_fixes.extend([
            # l to !
            (re.compile(u'({}{{3,}})[li]\\.\\.'.format(REGEX_LETTER), flags=re.UNICODE), r'\1!..', u'l-or-i-to-!',),
	])
class BaseSpellChecker(object):
    
    def __init__(self):
        self.log_file = 'automatic_fixes.log'
        self.format_string = u'{:30} {:30} {:30} {:30}\n'

    def quick_fix(self, word):
        """ Takes a string and returns the 'quick fix' version."""
        new_word = word
        for regex, replace, explanation in self.fixer.quick_fixes:
            new_word = re.sub(regex, replace, word)
            if new_word != word:
                self.log_fix('quick_fix', explanation, word, new_word)
                word = new_word
        return new_word

    def odd_punctuation(self, word):
        # Note: can return True even if would be fixed by fix spelling
        for regex in self.fixer.odd_punctuation:
            if regex.search(word):
                return True
        return False

    def hyphenate(self, word, min_chars=3):
        """ See if adding a hyphen or replacing
        a character with a hyphen helps.

        Will only hyphenate if min_chars (default 3) or more characters
        on each side."""
        
	spell_version = _decode(' '.join(self.check_line(word)))
        # don't fix if it isn't broken
        # don't fix if could not have minimum characters
        # on each side
        if not spell_version or len(spell_version) < 2*min_chars:
            return word
        fixed_versions = []
        # first try replacing characters
        for idx, char in enumerate(word):
            if idx < min_chars or len(word) - idx < min_chars + 1:
                continue
            new_word = u'{}{}{}'.format(
                word[:idx],
                '-',
                word[idx + 1:]
            )
            fixed_versions.append((new_word, 'hyphen-at-{}'.format(idx),))
	if fixed_versions:
            fixed_words = [t[0] for t in fixed_versions]
            bad_versions = [_decode(v) for v in self.check_line(' '.join(fixed_words))]
            good_versions = [item for item in fixed_words if item not in bad_versions]
        else:
            good_versions = []
        if good_versions:
            explanation = [t[1] for t in fixed_versions if t[0] == good_versions[0]][0]
            self.log_fix('spell_fix', explanation, spell_version, good_versions[0])
            return word.replace(spell_version, good_versions[0])
	# try individual fixes
        for regex, replace, explanation in self.fixer.punctuation_fixes:

            new_word, count = regex.subn(replace, word)
            # don't bother if nothing changed
            if count == 0:
                continue
            # if it fixes the problem, return it!
            if not self.check_line(new_word):
                self.log_fix('spell_fix', explanation, word, new_word)
                return new_word
        # give up - cannot fix
        return word

        # Then try adding a hyphen -- this is causing more problems than fixing
#       for idx, char in enumerate(word):
#           if idx < min_chars or len(word) - idx < min_chars:
#               continue
#           new_word = u'{}{}{}'.format(
#               word[:idx],
#               '-',
#               word[idx:]
#           )
#           # if it fixes the problem, return it!
#           if not self.check_line(new_word):
#               self.log_fix('force_hyphen_fix', 'hyphen-at-{}'.format(idx), word, new_word)
#               return new_word
        
    def fix_spelling(self, word):
        """ Run through the fixer's fixes and return
        a new word if it passes spell check."""
        

	# sometimes the spell checker does
	# not return the entire word
	spell_version = u' '.join(self.check_line(word))
        # don't fix if it isn't broken
        if not spell_version:
            return word
	fixed_versions = []
        for regex, replace, explanation in self.fixer.letter_fixes:

            # try replace all first
            new_word, count = regex.subn(replace, spell_version)
            # don't bother if nothing changed
            if count == 0:
                continue
            fixed_versions.append((new_word, explanation,))
            # try replacing one at a time
            if count > 1:
                for match in regex.finditer(spell_version):
                    new_word = u'{}{}{}'.format(
                        spell_version[:match.start()],
                        replace,
                        spell_version[match.end():]
                    )
                    fixed_versions.append((new_word, explanation,))
            # try replacing between one and all - TODO
	if fixed_versions:
            fixed_words = [t[0] for t in fixed_versions]
            bad_versions = [_decode(v) for v in self.check_line(' '.join(fixed_words))]
            good_versions = [item for item in fixed_words if item not in bad_versions]
        else:
            good_versions = []
        if good_versions:
            explanation = [t[1] for t in fixed_versions if t[0] == good_versions[0]][0]
            self.log_fix('spell_fix', explanation, spell_version, good_versions[0])
            return word.replace(spell_version, good_versions[0])
        else:
            # give up - cannot fix
            return word

    def odd_orthography(self, word1, word2):
        """ Returns True if the orthography is a little weird."""
         

    def log_fix(self, context, expression, old_word, new_word):
        with codecs.open(self.log_file, mode='ab', encoding='utf-8') as f:
            f.write(self.format_string.format(context, expression, old_word, new_word))

class StubSpellChecker(BaseSpellChecker):
    def __init__(self, correct_words):
	super(BaseSpellChecker, self).__init__()
        self.correct_words = correct_words
        self.fixer = BaseSpellFixer()
	self.log_file = '/var/tmp/test.log'
	self.format_string = ''

    def check_line(self, line):
        words = re.split('\s+', line, flags=re.UNICODE)
        return [word for word in words if word and not word in self.correct_words]


class AspellSpellChecker(BaseSpellChecker):
    def __init__(self, lang, dict_path=None):
        super(AspellSpellChecker, self).__init__()
        self.lang = lang
        self.aspell_command = ['aspell', 'list', '-l', self.lang,]
        if dict_path:
            self.aspell_command.append('-p')
            self.aspell_command.append(dict_path)
            self.dict_path = dict_path
        else:
            self.dict_path = None
        if lang[:2] == 'en':
            self.fixer = EnglishSpellFixer()
        elif lang[:2] == 'fr':
            self.fixer = FrenchSpellFixer()
        else:
            self.fixer = BaseSpellFixer()
    
    def interactive_check(self, path):
        command = ['aspell', '-c', '-l', self.lang,]
        if self.dict_path:
            command.extend(['-p', self.dict_path,])
        command.append(path)
#       Popen(command) 
        return command

    def add_word(self, word):
        if self.dict_path:
            with codecs.open(self.dict_path, mode='ab', encoding='utf-8') as f:
                f.write(word)
                f.write('\n')
             
    def check_line(self, line):
        p1 = Popen(['echo', line,], stdout=PIPE)
        p2 = Popen(self.aspell_command, stdin=p1.stdout, stdout=PIPE)
        p1.stdout.close()
        o = p2.communicate()[0]
        return o.split()

    def check_document(self, filename):
        p1 = Popen(['cat', filename,], stdout=PIPE)
        p2 = Popen(self.aspell_command, stdin=p1.stdout, stdout=PIPE)
        p1.stdout.close()
        o = p2.communicate()[0]
        return o.split()

class AlreadyCheckedSpellChecker(BaseSpellChecker):
    """ For when fixing things is alread done.
    Will check for odd punctuation.
    """
    def __init__(self, fixer=BaseSpellFixer()):
        self.fixer = fixer
    def check_line(self, line):
        # Always say it is good
        return False
    def quick_fix(self, word):
        return word
    def fix_spelling(self, word):
        return word
    def hyphenate(self, word):
        return word

def _decode(word):
    """ Returns the word maybe decoded to utf-8."""
    try:
        return word.decode('utf-8') 
    except UnicodeEncodeError:
        return word