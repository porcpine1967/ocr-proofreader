#!/usr/bin/env python
""" Contains classes that implement a spell-checking interface:
* given a string, return the mis-spelled words
* given a string, return whether it is 'garbage'
"""

import codecs
import os
import re
from subprocess import Popen, PIPE

from regex_helper import REGEX_LETTER, REGEX_CAPITAL, REGEX_SMALL, FRENCH_BAD_SINGLES, ENGLISH_BAD_SINGLES

begins_with_lowercase = re.compile(REGEX_SMALL, re.UNICODE).match
ends_with_lowercase = re.compile(u'.*{}$'.format(REGEX_SMALL), re.UNICODE).match
ends_with_hyphen = re.compile(r'.*-$', re.UNICODE).match
starts_with_capital = re.compile(u'["\']?{}'.format(REGEX_CAPITAL), re.UNICODE).match
starts_with_lower_case = re.compile(u'["\']?{}'.format(REGEX_SMALL), re.UNICODE).match

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
            (re.compile(u'([^=<~\xbb\u2014\u2013-])[=<~\xbb\u2014\u2013-]+$', flags=re.UNICODE), r'\1-', 'hyphen-at-end-of-line',),
            # hyphen between letters
            (re.compile(u'({})[=<~\u2014\u2013\xbb-]+({})'.format(REGEX_SMALL, REGEX_SMALL), flags=re.UNICODE), r'\1-\2', 'hyphen-between-letters',),
            # hyphen anywhere
            (re.compile(u'[~\u2014\u2013\xbb]+', flags=re.UNICODE), '-', 'hyphen-anywhere',),
            # weird combined f
            (re.compile(u'\ufb01', flags=re.UNICODE), 'fi', 'weird-fi',),
            (re.compile(u'\ufb02', flags=re.UNICODE), 'fl', 'weird-fl',),
            # weird small x
            (re.compile(u'\xd7', flags=re.UNICODE), 'x', 'weird-x',),
            # smart quotes and accents to dumb quotes
            (re.compile(u'[\u2019\u2018\u0060\u00B4]', flags=re.UNICODE), "'", 'smart-to-single-quote',),
            (re.compile(u'[\u201c\u201d]', flags=re.UNICODE), '"', 'smart-to-double-quote',),
            (re.compile(u'_?]({}+)'.format(REGEX_SMALL), flags=re.UNICODE), r'J\1', 'to-J',),
            # I-I or I-l to H
            (re.compile(u'I-[Il]({}+)'.format(REGEX_SMALL), flags=re.UNICODE), r'H\1', 'to-H',),
        ]
        self.letter_fixes = [
            (re.compile(r'\\/', flags=re.UNICODE), r'v', u'slashes-to-v',),
            (re.compile(r'rn', flags=re.UNICODE), r'm', u'rn-to-m',),
            (re.compile(r'm', flags=re.UNICODE), r'rn', u'm-to-rn',),
            (re.compile(r'ri', flags=re.UNICODE), r'n', u'ri-to-n',),
            (re.compile(u'({})O'.format(REGEX_LETTER), flags=re.UNICODE), r'\1o', u'XO-to-Xo',),
            (re.compile(r'ck', flags=re.UNICODE), u'd', u'ck-to-d',),
            (re.compile(r'cl', flags=re.UNICODE), u'd', u'cl-to-d',),
            (re.compile(r'lll\b', flags=re.UNICODE), u"'ll", u'lll-to-\'ll',),
            (re.compile(r'lf', flags=re.UNICODE), u'ff', u'lf-to-ff',),
            (re.compile(r'fl', flags=re.UNICODE), u'ff', u'fl-to-ff',),
            (re.compile(r'if', flags=re.UNICODE), u'ff', u'if-to-ff',),
            (re.compile(r'fi', flags=re.UNICODE), u'ff', u'fi-to-ff',),
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
            # Single right-pointed angle quotation mark inside a word
            re.compile(u'{}\u203A{}'.format(REGEX_SMALL, REGEX_SMALL), flags=re.UNICODE),
            # begin parenthesis directly after a letter
            re.compile(u'{}+\\('.format(REGEX_LETTER), flags=re.UNICODE),
            # end parenthesis followed directly by a letter
            re.compile(u'\\){}'.format(REGEX_LETTER), flags=re.UNICODE),
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
            # word beginning 1'
            re.compile(r"\b1'", flags=re.UNICODE),
        ]
	self.strict_checks = [
            re.compile(r'[0-9]', flags=re.UNICODE),
            re.compile(r'-$', flags=re.UNICODE),
            re.compile(r'<', flags=re.UNICODE),
            re.compile(r'>', flags=re.UNICODE),
            re.compile(u'\xbb', flags=re.UNICODE),
            re.compile(r'_', flags=re.UNICODE),
            re.compile(r'\*', flags=re.UNICODE),
            re.compile(r'\[', flags=re.UNICODE),
            re.compile(u'\xab\\S', flags=re.UNICODE),
            re.compile(r'\. \.', flags=re.UNICODE),
            re.compile(r' \.$', flags=re.UNICODE),
            re.compile(r' ,$', flags=re.UNICODE),
            re.compile(r"\s'", flags=re.UNICODE),
            re.compile(r"'\s", flags=re.UNICODE),
            re.compile(r"\s-[^\s]", flags=re.UNICODE),
            re.compile(r"[^\s]-\s", flags=re.UNICODE),
            re.compile(r'(^|\s)"($|\s)', flags=re.UNICODE),
	]	

	self.ends_sentence = re.compile(r'.*[.?!]["\')]?$', re.UNICODE).match
        self.propers = re.compile(u'\w[^.!?]*?((?:[ ,-]?{}\w*)+)'.format(REGEX_CAPITAL), flags=re.UNICODE).findall
        self.not_propers = re.compile(u', ["\']{}'.format(REGEX_CAPITAL), flags=re.UNICODE)
        self.bad_lowers =  re.compile(u'(?:[.!]|\?[^"])\W*({}\w*)'.format(REGEX_SMALL, REGEX_SMALL), flags=re.UNICODE).findall
        self.garbage_strippers = [
            (re.compile(r'"', flags=re.UNICODE), ''),
            (re.compile(r'[;:,.!?]$', flags=re.UNICODE), ''),
            (re.compile(r"'[ds]$", flags=re.UNICODE), ''), 
            (re.compile(r'(...)-.*', flags=re.UNICODE), r'\1'),
        ]   

class SimpleEnglishSpellFixer(BaseSpellFixer):
    def __init__(self):
        super(SimpleEnglishSpellFixer, self).__init__()
        self.letter_fixes = [
            (re.compile(r'0'), u'o', '',),
            (re.compile(r'l'), u'f', '',),
            (re.compile('rn'), u'm', '',),
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

        self.strict_checks.extend([
            re.compile(u"(^|[^'])\\b{}\\b".format(ENGLISH_BAD_SINGLES), flags=re.UNICODE),
            re.compile(r"[^s.]'($|\s)", flags=re.UNICODE),
            re.compile(r"\s'", flags=re.UNICODE),
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
            # replace a with a accent grave
            (re.compile(u'a', flags=re.UNICODE), u'\u00E0', u'a-to-\u00E0',),
            # replace a-tilde with a circumflex
            (re.compile(u'\u00E1', flags=re.UNICODE), u'\u00E2', u'a-to-\u00E2',),
            # replace e with e accent acute
            (re.compile(u'e', flags=re.UNICODE), u'\u00E9', u'e-to-\u00E9',),
            # replace e with e accent grave
            (re.compile(u'e', flags=re.UNICODE), u'\u00E8', u'e-to-\u00E8',),
            # replace accented i with plain i
            (re.compile(u'\u00EC', flags=re.UNICODE), u'i', u'odd-i-to-i',),
            # replace i with i accent grave
            (re.compile(u'i', flags=re.UNICODE), u'\u00EC', u'i-to-\u00EC',),
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
            # .V to J'
            (re.compile(u'\\.V({}{{3,}})'.format(REGEX_SMALL), flags=re.UNICODE), r"J'\1", u'.V-to-J-appos',),
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
            # l to !
            (re.compile(u'({}{{3,}})[li]\\b'.format(REGEX_LETTER), flags=re.UNICODE), r'\1!', u'l-or-i-to-!',),
            # qu- to qu'
            (re.compile(u'\\b([Qq]u)-({}{{3,}})'.format(REGEX_SMALL), flags=re.UNICODE), r"\1'\2", u'qu-dash-to-qu-appos',),
            # lsnmdJ- to lsnmdJ'
            (re.compile(u'\\b([LlsnJmd])-({}{}{{2,}})'.format(REGEX_LETTER, REGEX_SMALL), flags=re.UNICODE), r"\1'\2", u'lsnmJd-dash-to-ldsnmJ-appos',),
            # nf- to m'
            (re.compile(u'\\bnf({}{{3,}})'.format(REGEX_SMALL), flags=re.UNICODE), r"m'\1", u'nf-to-m-appos',),
            # 1(-') to l(-')
            (re.compile(u"\\b1[-']({}{}{{2,}})".format(REGEX_LETTER, REGEX_SMALL), flags=re.UNICODE), r"l'\1", u'1-dash-to-l-appos',),
            # xXx to xxx
            (re.compile(u'{}{}{}'.format(REGEX_SMALL, REGEX_CAPITAL, REGEX_SMALL), flags=re.UNICODE), lambda m: m.group(0).lower(), 'xXx-to-xxx'),
        ])

	self.punctuation_fixes.extend([
            # l to !
            (re.compile(u'({}{{3,}})[li]\\.\\.'.format(REGEX_LETTER), flags=re.UNICODE), r'\1!..', u'l-or-i-to-!',),
	])
	self.strict_checks.extend( [
            re.compile(r'"', flags=re.UNICODE),
#           re.compile(u"\\b[bcdefghijklmnopqrstuvwxzBCDEFGHIJKLMNOPQRSTUVWXYZ]\\b[^'-]", flags=re.UNICODE),
            re.compile(u"\\b{}\\b($|[^'-])".format(FRENCH_BAD_SINGLES), flags=re.UNICODE),
        ])
	self.ends_sentence = re.compile(u'.*[.:?!](["\')]|[\u203A\xAB-]+)?$', re.UNICODE).match
        self.propers = re.compile(u'\w[^.:!?]*?((?:[ ,-]?{}(?:\'|\w*))+)'.format(REGEX_CAPITAL), flags=re.UNICODE).findall
        self.bad_lowers =  re.compile(u'\.\W*({}\w*)'.format(REGEX_SMALL), flags=re.UNICODE).findall

class BaseSpellChecker(object):
    
    def __init__(self):
        self.log_file = 'automatic_fixes.log'
        self.format_string = u'{:30} {:30} {:30} {:30}\n'
        self.line_join_fixes = {}

    def strip_garbage(self, word):
        """ Removes words useless for proper name comparison."""
        hold_word = word
        for regex, repl in self.fixer.garbage_strippers:
            word = regex.sub(repl, word)
#       if word != hold_word:
#           print word
        return word

    def strict_check(self, line):
        """ Takes a string and returns an array of strict matches."""
        strict_matches = set()
        for regex in self.fixer.strict_checks:
            m = regex.search(line)
            if m:

#               print regex.pattern
                strict_matches.add(m.group(0))

        return strict_matches

    def quick_fix(self, word):
        """ Takes a string and returns the 'quick fix' version."""
        new_word = word
        for regex, replace, explanation in self.fixer.quick_fixes:
            new_word = re.sub(regex, replace, word)
            if new_word != word:
                self.log_fix('quick_fix', explanation, word, new_word)
                word = new_word
        return new_word

    def odd_punctuation(self, line):
        # Note: can return True even if would be fixed by fix spelling
        odd = set()
        for regex in self.fixer.odd_punctuation:
            m = regex.search(line)
            if m:
                odd.add(m.group(0))
        return odd


    def hyphenated_versions(self, word, min_chars=3):
        hyphenates = []
        # try replacing characters
        for idx, char in enumerate(word):
            if idx < min_chars or len(word) - idx < min_chars + 1:
                continue
            new_word = u'{}{}{}'.format(
                word[:idx],
                '-',
                word[idx + 1:]
            )
            if not '--' in new_word:
                hyphenates.append((new_word, 'hyphen-at-{}'.format(idx),))
        return hyphenates

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

        fixed_versions = self.hyphenated_versions(word, min_chars)

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
    def failed_words(self, to_check):
        """ Given an array of words, returns array of same length, with the
        'good' words blank and the 'bad' words what the spell checker
        thinks is a bad word.

        Because the spell checker might not preserve punctuation, we
        can't do simple substitution of bad and good words.

        Note: because what the line manager thinks is one word might be construed
        as two words by the spell checker, any thing using this should probably
        split the results.
        """
        self.output_dir = 'working'
        with codecs.open('{}/hold_words.tmp'.format(self.output_dir), mode='wb', encoding='utf-8') as f:
            f.write(u' xNoTPassx '.join(to_check))
        # aspell maintains order of bad words, but does not return good words
        # we therefore need some way to indicate that nothing was returned
        # (that is the word was good) in a given area.  This is noted by
        # a repetition of xNoTPassx
        # We then split on that, which leaves empty strings in the space
        # that have good words (which fail a boolean test in python)
        failed_versions = self.check_document('{}/hold_words.tmp'.format(self.output_dir))
        return u''.join([_decode(w) for w in failed_versions]).split(u'xNoTPassx')

    def good_and_bad(self, to_check):
        """ Given an array (order is important) of words returns good and bad collections.

        First is a collection of correctly spelled words. 
        Second is a collection of misspelled words.
        """
        failed_words = self.failed_words(to_check)
        good_versions = []
        bad_versions = []
        for idx, w in enumerate(to_check):
            if not failed_words[idx]:
                good_versions.append(w)
            else:
                bad_versions.append(w)
        return good_versions, bad_versions

    def transformed_variations(self, word, append=True):
        """ Run through the fixer's fixes and return all variations.
        append means run through variations of variations, called
        with false when too many transformations are happening
        """
	changed_versions = [(word, '', ''),]
	versions_to_fix = [(word, '', ''),]
        for regex, replace, explanation in self.fixer.letter_fixes:
            if append:
                versions_to_fix = changed_versions
            if len(versions_to_fix) > 200:
                return self.transformed_variations(word, False)
            
            for potential_fix, old_word, provided_explanation in versions_to_fix:
                existing_words = [group[0] for group in changed_versions]
                # try replace all first
                new_word, count = regex.subn(replace, potential_fix)
                # don't bother if nothing changed
                if count == 0:
                    continue
                if new_word not in existing_words:
                    changed_versions.append((new_word, potential_fix, explanation,))
                # try replacing one at a time
                if count > 1: # and u'\\' not in replace:
                    for match in regex.finditer(potential_fix):

                        new_word_2 = u'{}{}{}'.format(
                            potential_fix[:match.start()],
                            match.expand(replace),
                            potential_fix[match.end():]
                        )
                        if new_word_2 not in existing_words:
                            changed_versions.append((new_word_2, potential_fix, explanation,))
            changed_versions = list(set(changed_versions))
                # try replacing between one and all - TODO
        changed_versions.remove((word, '', ''))
#       for hyphenate in self.hyphenated_versions(word):
#           changed_versions.append((hyphenate[0], word, hyphenate[1],))
        return set(changed_versions)

    def fix_spelling(self, word):
        """ Run through the fixer's fixes and return
        a new word if it passes spell check."""
        # sometimes the spell checker does
        # not return the entire word
        spell_version = u' '.join(self.check_line(word))
         # don't fix if it isn't broken
        if not spell_version:
            return word
        
        changed_versions = self.transformed_variations(word)

        good_versions = []
	if changed_versions:
            changed_words = [t[0] for t in changed_versions]
            # aspell maintains order of bad words, but does not return good words
            # we therefore need some way to indicate that nothing was returned
            # (that is the word was good) in a given area.  This is noted by
            # a repetition of xNoTPassx
            # We then split on that, which leaves empty strings in the space
            # that have good words (which fail a boolean test in python)
            failed_versions = [_decode(v) for v in self.check_line(u' xNoTPassx '.join(changed_words))]
            words_if_bad = ''.join(failed_versions).split(u'xNoTPassx')
            for idx, w in enumerate(changed_words):
                if not words_if_bad[idx]:
                    good_versions.append(w)
        if good_versions:
            explanation = [t[1] for t in changed_versions if t[0] == good_versions[0]][0]
            self.log_fix('spell_fix', explanation, spell_version, good_versions[0])
            return good_versions[0] #word.replace(spell_version, good_versions[0])
        else:
            # give up - cannot fix
            return word


    def proper_noun(self, preceding_word, word_to_check):
        """ Returns boolean on whether word_to_check is grammatically correct
        only if it is a proper noun."""
        if starts_with_capital(word_to_check):
            return not self.fixer.ends_sentence(preceding_word)
        elif starts_with_lower_case(word_to_check):
            return self.fixer.ends_sentence(preceding_word)
        else:
            return False
            
    def proper_nouns(self, line):
        """ Takes an array of lines and returns all proper nouns. """
        propers = []
        to_check = self.fixer.not_propers.sub('a', line)
        for proper in self.fixer.propers(to_check):
            propers.extend(w for w in re.split('[, -]', proper) if w)
        return propers

    def lower_after_sentence(self, line):
        """ Takes a string and looks for end punctuation followed by lowercase. """
        return self.fixer.bad_lowers(line)
 
    def odd_orthography(self, word_1, word_2):
        """ Returns True if the orthography is a little weird
        between word one and word two.
        """
        

    def log_fix(self, context, expression, old_word, new_word):
        with codecs.open(self.log_file, mode='ab', encoding='utf-8') as f:
            f.write(self.format_string.format(context, expression, old_word, new_word))


    def fix_line(self, line):
        """ Has all the words in the line fix themselves.

        Probably reciprocal (it would call the spell checker to fix),
        but overriden below."""
        line.build_words()
        for word in line.words:
            word.correct_spelling()
            word.hyphenate()
        line.rebuild()       

    def check_join(self, word_a, word_b):
        """ Returns easy fix under certain conditions.

        If word a ends with hyphen and word b lower case
        always returns something.
        if joining word a with word b without the hyphen
        passes spell check, returns joined words.
        else returns hyphenated version of word.
        """
        if ends_with_hyphen(word_a) and begins_with_lowercase(word_b):
            fixed_word = word_a[:-1] + word_b
            if self.check_line(fixed_word):
                return word_a + word_b
            else:
                return fixed_word
        else:
            return None

class StubSpellChecker(BaseSpellChecker):
    def __init__(self, correct_words, line_join_fixes={}):
	super(BaseSpellChecker, self).__init__()
        self.correct_words = correct_words
        self.fixer = BaseSpellFixer()
	self.log_file = '/var/tmp/test.log'
	self.format_string = ''
        self.line_join_fixes = line_join_fixes

    def check_line(self, line):
        words = re.split('\s+', line, flags=re.UNICODE)
        return [word for word in words if word and not word in self.correct_words]



    def check_document(self, filename):
        bad_words = []
        with codecs.open(filename, mode='rb', encoding='utf-8') as f:
            for l in f:
                bad_words.extend(self.check_line(l))
        return bad_words

                                 
class AspellSpellChecker(BaseSpellChecker):
    def __init__(self, lang, dict_path=None):
        super(AspellSpellChecker, self).__init__()
        self.lang = lang
        self.aspell_command = ['aspell', 'list', '-l', self.lang,]
        if dict_path and os.path.exists(dict_path):
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

class FileConfiguredSpellChecker(AspellSpellChecker):
    """ Uses Files created by document builder to check things."""
    def __init__(self, lang, dict_=None, dir_='working'):
        super(FileConfiguredSpellChecker, self).__init__(lang, dict_)
        self.load_word_fixes(dir_)
        self.load_line_join_fixes(dir_)

    def load_word_fixes(self, dir_):
        self.word_fixes = {}
        with codecs.open('{}/word_fixes.txt'.format(dir_), mode='rb', encoding='utf-8') as f:
            for l in f:
                key, value = l.split('|', 1)
                self.word_fixes[key] = value.strip()

    def load_line_join_fixes(self, dir_):
        self.line_join_fixes = {}
        with codecs.open('{}/line_join_fixes.txt'.format(dir_), mode='rb', encoding='utf-8') as f:
            for l in f:
                key, value = l.split('|', 1)
                self.line_join_fixes[key] = value.strip()

    def fix_spelling(self, word):
        try:
            return self.word_fixes[word]
        except KeyError:
            return word

    def fix_line(self, line):
	words = line.text.split()
        for idx, word in enumerate(words):
            words[idx] = self.fix_spelling(word)
        line.text = (u' '.join(words))

    def check_join(self, word_a, word_b):
        key = u'{}_{}'.format(word_a, word_b)
        try:
            return self.line_join_fixes[key]
        except KeyError:
            return None

def valid_joinables(first_word, second_word, checker):
    """ Only returns joinables if would join. """
                    
    if not begins_with_lowercase(second_word):
        return []
    if ends_with_hyphen(first_word) or \
        checker.check_line(' '.join([first_word, second_word,])):
        return joinables(first_word, second_word)
    return []

def joinables(first_word, second_word):
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
