#!/usr/bin/env python
from argparse import ArgumentParser
import codecs
from collections import Counter
from ConfigParser import ConfigParser, NoOptionError
import csv
import Image
import os
import re
import shutil
import sys

import comparison_manager
import controller
import process_pdf 
import document_builder
import line_manager
import spell_checker
import dpgui
import gui
import gui2
import gui3
import gui4
import gui5

def test():
    """ Whatever is being worked on."""
    """ Currently, either proper nouns or cross-line fixes."""
#   page_info()
#   remove_headers()
#   proper_names()
#   check_if_ok()
#   examine_slices()

#   compare()
def compare():
    cm = comparison_manager.ComparisonManager()
    cm.histogram_2()

def examine_page(page_nbr):
    p = document_builder.PageInfo(
        'images/pages/{}.pbm'.format(page_nbr),
        'text/raw/{}.txt'.format(page_nbr)
        )
    p.grid_version('page_{}.png'.format(page_nbr))
def examine_slices():
    page_nbr = 277
    im = Image.open('images/pages/{}.pbm'.format(page_nbr))
    with open('working/page_info/{}.csv'.format(page_nbr), 'rb') as f:
        reader = csv.reader(f)
        for idx, row in enumerate(reader):
            if int(row[0]) == page_nbr:
                line_info = line_manager.LineInfo(int(row[3]))
                line_info.height = int(row[1])
                line_info.left_margin = int(row[2])
                line_info.width = int(row[4])
                im2 = line_info.image(im)
                im2.save('test_{}.jpg'.format(idx), 'jpeg')
    

def check_if_ok():
    lang = get_lang()
    lm = line_manager.LineManager(
        spell_checker.AspellSpellChecker(lang)
        )
    lm.load('text/clean')
    good = []
    skipped = []
    skipping = False
    with codecs.open('working/maybe_ok.txt', mode='rb', encoding='utf-8') as f:
        for l in f:
            if skipping:
                skipped.append(l)
                continue
            word = l.split()[0]
            page_nbr, line, line_info = lm.find_word(word)
            if line:
                print 'Page:', page_nbr
                print 'Word:', word
                print line.text
                if line_info:
                    im = Image.open('images/pages/{}.pbm'.format(page_nbr))
                    im2 = line_info.image(im, 2)
                    im2.save('test.jpg', 'jpeg')
                result = raw_input()
                if result == 'y':
                    good.append(word)
                elif result == 's':
                    skipped.append(l)
                elif result == 'q':
                    skipping = True
                    skipped.append(l)

    with codecs.open('working/good.txt', mode='ab', encoding='utf-8') as f:
        for g in good:
            f.write(u'{}\n'.format(g))

    with codecs.open('working/maybe_ok.txt', mode='wb', encoding='utf-8') as f:
        for skip in skipped:
            f.write(skip)

def page_info():
    lang = get_lang()
    checker = spell_checker.AspellSpellChecker(lang)
    db = document_builder.SpellcheckDocMaker(checker)
    db.page_image_info('text/raw', 'images/pages')

def possible_headers():
    lang = get_lang()
    checker = spell_checker.AspellSpellChecker(lang)
    db = document_builder.SpellcheckDocMaker(checker)
    db.possible_headers('text/raw')

def proper_names():
    lang = get_lang()
    dict_ = './dict.{}.pws'.format(lang)
    checker = spell_checker.AspellSpellChecker(lang, dict_)
    db = document_builder.SpellcheckDocMaker(checker)
    db.make_possible_proper_name_doc('text/clean')
    
def cross_line_fixes():
    lang = get_lang()
    checker = spell_checker.AspellSpellChecker(lang)
    db = document_builder.SpellcheckDocMaker(checker)
    db.make_line_join_doc('text/clean')

def fix_spells():
    """ Runs through the document, finds all the bad words, then 
    tries to find fixed versions of them.
    """
    lang = get_lang()
    checker = spell_checker.AspellSpellChecker(lang)

    db = document_builder.SpellcheckDocMaker(checker)
    db.make_word_fix_doc('text/clean')

def run_gui2():
    """ Batch cleans the pages in text/clean."""
    lang = get_lang()
    lm = line_manager.LineManager(
        spell_checker.AspellSpellChecker(lang)
        )
    lm.load('text/clean')
    gui2.main(lm)

def run_gui3():
    """ Batch cleans the pages in text/clean."""
    config = ConfigParser()
    config.read('book.cnf')
    if config.has_option('process', 'last_html_page'):
        start_page = config.getint('process', 'last_html_page')
    else:
        start_page = 0
    lang = get_lang()
    lm = line_manager.LineManager(
        spell_checker.AspellSpellChecker(lang),
        start_page
        )
    lm.load('text/clean')
    app = gui3.main(lm)
    last_page = int(app.last_html_page)
    last_line = app.last_html_line
    lm.write_html(config, int(last_page), int(last_line))
    if last_page >= start_page:
        config.set('process', 'last_html_page', last_page)
        config.set('process', 'last_html_line', last_line)
    with open('book.cnf', 'wb') as f:
        config.write(f)

def run_gui4():
    
    """ Checks for proper noun problems."""
    config = ConfigParser()
    config.read('book.cnf')
    if config.has_option('process', 'last_proper_page'):
        start_page = config.getint('process', 'last_proper_page')
    else:
        start_page = 0
    lang = get_lang()
    lm = line_manager.LineManager(
        spell_checker.AspellSpellChecker(lang),
        start_page
        )
    lm.load('text/clean')
    app = gui4.main(lm)
    lm.write_pages('text/clean', False)
    last_page = int(app.last_page)
    if last_page >= start_page:
        config.set('process', 'last_proper_page', last_page)
    with open('book.cnf', 'wb') as f:
        config.write(f)

def run_gui5(page_nbr):
    app = gui5.main(page_nbr)

def run_dpgui():
    lang = get_lang()
    lm = line_manager.LineManager(
        spell_checker.AspellSpellChecker(lang, './dict.{}.pws'.format(lang))
        )
    lm.load('text/clean')
    dpgui.main(lm)
    lm.write_pages('text/clean', False)

def run_gui(input_start_page, end_page, strict):
    """ Batch cleans the pages in text/clean."""
    config = ConfigParser()
    config.read('book.cnf')
    if strict and \
        config.has_option('process', 'last_strict_page'):
        hold_page = config.getint('process', 'last_strict_page')
    elif not strict and \
        config.has_option('process', 'last_checked_page'):
        hold_page = config.getint('process', 'last_checked_page')
    else:
        hold_page = input_start_page
    print hold_page
    if input_start_page == 0:
        start_page = hold_page
    else:
        start_page = input_start_page
    lang = get_lang()
    lm = line_manager.LineManager(
        spell_checker.AspellSpellChecker(lang, './dict.{}.pws'.format(lang)),
        start_page,
        end_page
        )
    lm.load('text/clean')
    app = gui.main(lm, strict)
    lm.write_pages('text/clean', False)

    if strict and int(app.last_page) >= hold_page:
        config.set('process', 'last_strict_page', app.last_page)
    elif not strict and int(app.last_page) >= hold_page:
        config.set('process', 'last_checked_page', app.last_page)
    with open('book.cnf', 'wb') as f:
        config.write(f)
    
def new():
    """ Create/update config, dictionary, and file structure."""
    # Set up pdfs
    if not os.path.exists('pdfs'):
        os.mkdir('pdfs')
        for filename in os.listdir('.'):
            print filename
            if filename.endswith('pdf') or filename.endswith('tiff'):
                shutil.move(filename, 'pdfs')
    
    # Set up/update config
    config = ConfigParser()
    # Load config if it already exists
    if os.path.exists('book.cnf'):
        config.read('book.cnf')
    set_up_sections(config)
    batch_configuration(config)
    interactive_configuration(config)
    with open('book.cnf', 'wb') as f:
        config.write(f)

    # Make sure dictionary exists
    lang = get_lang()
    print 'Initialization Complete'

def set_up_sections(config):
    """ Make sure the configuration sections are present."""
    sections = (
        'extract_text',
        'metadata',
        'process',
    )   
    for section in sections:
        if not config.has_section(section):
            config.add_section(section)

def batch_configuration(config):
    """ Add all configurations we know the answer to."""
    if not config.has_option('process', 'clean_headers'):
        config.set('process', 'clean_headers', 'true')

def interactive_configuration(config):
    """ Ask about the configurations we need answers for."""
    if not config.has_option('extract_text', 'start_page_number'):
        print 'Indicate with which page number the book should start'
        sys.stdout.write('> ')
        result = raw_input()
        config.set('extract_text', 'start_page_number', int(result))

    if not config.has_option('extract_text', 'ordered_dirnames'):
        pdfs = [os.path.splitext(filename)[0] for filename in os.listdir('pdfs') ]
        pdf_map = {}
        for idx, pdf in enumerate(sorted(pdfs)):
            pdf_map[idx + 1] = pdf
        for idx, pdf in sorted(pdf_map.items(), key=lambda x: x[0]):
            print '{:>2}. {}'.format(idx, pdf)
        while (True):
            print 'Type the numbers in the order the pdfs should be processed.'
            print 'Example: 2 3 1 4'
            sys.stdout.write('> ')
            result = raw_input()
            try:
                page_numbers = [int(nbr) for nbr in result.split()]
                if sorted(page_numbers) == sorted(pdf_map.keys()):
                    ordered_dirnames = []
                    for page_number in page_numbers:
                        ordered_dirnames.append(pdf_map[page_number])
                    print 'Is this order correct?'
                    for dirname in ordered_dirnames:
                        print dirname
                    sys.stdout.write('> ')
                    result = raw_input()
                    if result.lower().startswith('y'):
                        config.set('extract_text', 'ordered_dirnames', ' '.join(ordered_dirnames))
                        break
            except ValueError:
                pass
            print 'Please try again\n'

    if not config.has_option('extract_text', 'ignore_pages'):
        first_dir_name = config.get('extract_text', 'ordered_dirnames').split()[0]
        while (True):
            print 'How many pages at the beginning of the book should be skipped?'
            sys.stdout.write('> ')
            result = raw_input()
            try:
                pages_to_skip = []
                for i in xrange(int(result)):
                    plate, second_page = divmod(i, 2)
                    page = second_page and 'b' or 'a'
                    skip = '{}/{}-{:03}-{}.pbm'.format(first_dir_name, first_dir_name, plate, page) 
                    pages_to_skip.append(skip)
                print 'Is this correct?'
                for skip in pages_to_skip:
                    print skip
                sys.stdout.write('> ')
                result = raw_input()
                if result.lower().startswith('y'):
                    config.set('extract_text', 'ignore_pages', ' '.join(pages_to_skip))
                    break
            except ValueError:
                pass
            print 'Please try again\n'

    # These are all simple strings that use the same logic for setting
    fillables = (
        ('extract_text', 'lang', 'What language is the book written in? (Please use aspell abbreviation)'),
        ('metadata', 'title', 'What is the title of the book?'),
        ('metadata', 'author', 'Who is the author of the book?'),
        ('metadata', 'html_file', 'What would you like the html file to be called?'),
        
    )
    for section, key, question in fillables:
        if not config.has_option(section, key):
            while (True):
                print question
                sys.stdout.write('> ')
                result = raw_input()
                value = result.strip()
                if value:
                    print 'Is this correct?'
                    sys.stdout.write('> ')
                    result = raw_input()
                    if result.lower().startswith('y'):
                        config.set(section, key, value)
                        break
                print 'Please try again\n'

def remove_headers():
    lang = get_lang()
    dict_ = './dict.{}.pws'.format(lang)
    checker = spell_checker.AspellSpellChecker(lang, dict_)
    db = document_builder.SpellcheckDocMaker(checker)
    db.remove_possible_headers('text/clean')

def _loaded_file_line_manager(start_page, end_page):
    """ Returns loaded line manager with aspell spell checker."""
    lang = get_lang()
    lm = line_manager.LineManager(
        spell_checker.FileConfiguredSpellChecker(lang),
        start_page,
        end_page
        )
    lm.load('text/clean')
    return lm
def _loaded_aspell_line_manager(start_page, end_page):
    """ Returns loaded line manager with aspell spell checker."""
    lang = get_lang()
    lm = line_manager.LineManager(
        spell_checker.AspellSpellChecker(lang),
        start_page,
        end_page
        )
    lm.load('text/clean')
    return lm
def simple_clean():
    """ Simple cleanup for testing algorithm. """
    os.system('cp text/raw/* text/simple_clean/')
    lang = get_lang()
    checker = spell_checker.AspellSpellChecker(lang)
#   checker.fixer = spell_checker.SimpleEnglishSpellFixer()
    db = document_builder.SpellcheckDocMaker(checker)
    db.remove_possible_headers('text/simple_clean')
    lm = line_manager.LineManager(
        spell_checker.FileConfiguredSpellChecker(lang)
        )
    lm.load('text/simple_clean')
    lm.quick_fix()
    lm.join_lines()
#   lm.write_pages('text/simple_clean', False)
#   db.make_word_fix_doc('text/simple_clean')
    lm.write_pages('text/simple_clean', True)

def clean(start_page, end_page):
    """ Batch cleans the pages in text/clean."""

    config = ConfigParser()
    config.read('book.cnf')
    try:
        clean_headers = config.getboolean('process', 'clean_headers')
    except NoOptionError:
        clean_headers = True
    try:
        join_lines = config.getboolean('process', 'join_lines')
    except NoOptionError:
        join_lines = True

    if clean_headers:
	print 'cleaning headers'
        remove_headers()
        if not config.has_section('process'):
            config.add_section('process')
        config.set('process', 'clean_headers', 'false')
        with open('book.cnf', 'wb') as f:
            config.write(f)
        lm =_loaded_aspell_line_manager(start_page, end_page)
        lm.quick_fix()
    elif join_lines:
	print 'joining lines'
        if not config.has_section('process'):
            config.add_section('process')
        config.set('process', 'join_lines', 'false')
        with open('book.cnf', 'wb') as f:
            config.write(f)
        lm =_loaded_file_line_manager(start_page, end_page)
        lm.join_lines()
    else:
        # if interrupted by keyboard, go ahead and write changes
        lang = get_lang()
#           spell_checker.FileConfiguredSpellChecker(lang, './dict.{}.pws'.format(lang)),
#           spell_checker.AspellSpellChecker(lang, './dict.{}.pws'.format(lang)),
        lm = line_manager.LineManager(
#           spell_checker.AspellSpellChecker(lang, './dict.{}.pws'.format(lang)),
            spell_checker.FileConfiguredSpellChecker(lang),
            start_page,
            end_page
            )
        lm.load('text/clean')
        try:
            lm.fix_lines()
        except KeyboardInterrupt:
            pass
    lm.write_pages('text/clean', False)

def extract_images(tiffs, verbose):
    if tiffs:
        pdf_processor = process_pdf.TiffProcessor(verbose)
    else:
        pdf_processor = process_pdf.PdfProcessor(verbose)
    pdf_processor.extract_images_from_pdfs()
    pdf_processor.extract_pages_from_images()
    
def extract_text(verbose):
    lang = get_lang()
    tesseract_lang = aspell_lang_to_tesseract_lang(lang)
    pdf_processor = process_pdf.PdfProcessor(verbose)
    pdf_processor.extract_text_from_pages(tesseract_lang)

def extract_pdf(verbose):
    pdf_processor = process_pdf.PdfProcessor(verbose)
    pdf_processor.expand_pdfs()
    pdf_processor.extract_text_from_pdf()
    pdf_processor.make_images_from_pdf()

def symlink_images(verbose):
    pdf_processor = process_pdf.PdfProcessor(verbose)
    pdf_processor.symlink_images()

def aspell_lang_to_tesseract_lang(aspell_lang):
    if aspell_lang.startswith('fr'):
        return 'fra'
    else:
    # default English
        return 'eng'

def aspell_clean():

    starts_with_cap = re.compile('^[A-Z]')
    lang = get_lang()
    checker = spell_checker.AspellSpellChecker(lang)
    bad_word_ctr = Counter()
    for fn in os.listdir('text/clean'):
        if fn.endswith('.txt'):
            for bad_word in checker.check_document('text/clean/{}'.format(fn)):
                bad_word_ctr[bad_word] += 1
    with codecs.open('working/maybe_ok.txt', mode='wb', encoding='utf-8') as f:
        for bad_word, count in bad_word_ctr.most_common():
            if starts_with_cap.match(bad_word):
                f.write(u'{} ({})\n'.format(spell_checker._decode(bad_word), count))
        for bad_word, count in bad_word_ctr.most_common():
            if not starts_with_cap.match(bad_word):
                f.write(u'{} ({})\n'.format(spell_checker._decode(bad_word), count))
        
def aspell_run(start, end):
    lang = get_lang()
    checker = spell_checker.AspellSpellChecker(lang)
    for fn in sorted(os.listdir('text/clean'), key=lambda x: int(os.path.splitext(x)[0])):
        
        basename, ext = os.path.splitext(fn)
        if int(basename) < start or ext != '.txt':
            continue

        if int(basename) > end:
            return
        command = checker.interactive_check('text/clean/{}'.format(fn)) 
        os.system(' '.join(command))
    os.system('rm text/clean/*.bak')

def get_lang():
    config = ConfigParser()
    config.read('book.cnf')
    return config.get('extract_text', 'lang')

def interactive_fix(start_page, end_page):
    lang = get_lang()
    lm = line_manager.LineManager(
        spell_checker.AspellSpellChecker(lang, './dict.{}.pws'.format(lang)),
        start_page,
        end_page
        )
    lm.load('text/clean')
    lm.interactive_fix()
    lm.write_pages('text/clean', False)


def write_html():    
    lm = line_manager.LineManager(spell_checker.AspellSpellChecker('en_GB', './dict.en.pws'))
    lm.load('text/clean')
    config = ConfigParser()
    with open('book.cnf', 'r') as cf:
        config.readfp(cf)
    lm.write_html(config)

def run():
    actions = (
        ('new', 'First thing to run.  Moves pdfs around and creates book.cnf'),
        ('extract_all', 'Extracts images and text'),
        ('extract_images', 'Extract page images from pdfs/tiffs'),
        ('extract_text', 'Extracts text from images'),
        ('extract_pdf', 'Extracts text from pdf, makes images of pages'),
        ('page_info', 'Writes out page info for mapping lines to image location'),
        ('spell_check', 'Writes maybe_ok file'),
        ('gui2', 'Looks for words in maybe_ok to see if should add to dict'),
        ('headers', 'Writes out possible headers and footers to files'),
        ('clean', 'First time, removes headers and quick fixes; then joins lines, then fixes spelling'),
        ('fix_spells', 'Looks for bad words, writes potential fixes to file'),
        ('fix_all', 'Runs fix spells and fix lines'),
        ('fix_lines', 'Looks for lines that should be joins and writes fixes to file'),
        ('gui', 'Interactive spelling error finder and fixer (plus search)'),
        ('odd_punctuation', 'Looks for odd punctuation'),
        ('html', 'gui for adding html tags'),
        ('gui3', 'g3'),
        ('dpgui', 'Gui for checking distributed proofreading texts'),
        ('interactive_spell_check', 'Runs aspell on files in text/clean'),
        ('page_grid', 'pg'),
        ('symlink_images', 'si'),
        ('test', 't'),
        ('simple_clean', 'sc'),
        ('fix', 'Interactive fix'),
        ('fix_page_info', 'Adjust the page info lines'),
    )
    parser = ArgumentParser(
        description="Tool for converting images of books into corrected text"
        )
    parser.add_argument('-a', type=str, 
        default='interactive',
        dest='action',
        help="Which action you want to do. Defaults to 'interactive'")
    parser.add_argument('-start', type=int,
        default=0,
        dest='start',
        help='What page to start on (defaults to first page)')
    parser.add_argument('-end', type=int,
        default=0,
        dest='end',
        help='What page to end on (defaults to last page)')
    parser.add_argument('-interval', type=int,
        default=30,
        dest='interval',
        help='How many pages to process in interactive mode (defaults to 10)')
    parser.add_argument('-language', type=str,
        default='en',
        dest='language',
        help='Sets the language for the initial configuration')    
    parser.add_argument('-v', type=bool,
        default=False,
        dest='verbose',
        help='Verbose: print out lots or little')
    parser.add_argument('-page-number', type=int,
        default='-1',
        dest='page_nbr',
        help='Page number for page grid')
    parser.add_argument('-strict', type=bool,
        default=False,
        dest='strict',
        help='In gui, whether to use strict checking')
    parser.add_argument('-tiffs', type=bool,
        default=False,
        dest='tiffs',
        help='when processing, if the image files are tiff format')
    args = parser.parse_args()
    acceptable_actions = [action[0] for action in actions]
    if args.action not in acceptable_actions:
        print 'Please provide one of the following actions:'
	for action, description in actions:
            print '{:>15}: {}'.format(action, description)
    elif args.action in ('new', 'n',):
        new()
    elif args.action in ('page_grid', 'pg',):
        if args.page_nbr < 0:
            print 'Need a -page-number'
        else:
            examine_page(args.page_nbr)
    elif args.action in ('extract_all', 'e',):
        extract_images(args.tiffs, args.verbose)
        extract_text(args.verbose)
    elif args.action in ('extract_images', 'i',):
        extract_images(args.tiffs, args.verbose)
    elif args.action in ('symlink_images', 'si',):
        symlink_images(args.verbose)
    elif args.action in ('extract_text', 't',):
        extract_text(args.verbose)
    elif args.action in ('extract_pdf', 'asfdasft',):
        extract_pdf(args.verbose)
    elif args.action in ('spell_check', 'a',):
        aspell_clean()
    elif args.action in ('page_info', 'pi',):
        page_info()
    elif args.action in ('clean', 'c',):
        clean(args.start, args.end) 
    elif args.action in ('fix', 'f',):
        if args.end == 0:
            end_page = args.start + args.interval - 1
        else:
            end_page = args.end
        interactive_fix(args.start, end_page)
    elif args.action in ('interactive_spell_check', 'p',):
        if args.end == 0:
            end_page = args.start + args.interval - 1
        else:
            end_page = args.end
        aspell_run(args.start, end_page)
    elif args.action in ('fix_all', 'ft',):
        fix_spells()
        cross_line_fixes()
    elif args.action in ('fix_spells', 'ft',):
        fix_spells()
    elif args.action in ('headers', 'hf',):
        possible_headers()
    elif args.action in ('fix_lines', 'ft',):
        cross_line_fixes()
    elif args.action in ('dpgui', 'dp',):
        run_dpgui()
    elif args.action in ('html', 'h',):
        run_gui3()
    elif args.action in ('gui', 'g'):
        if args.end == 1:
            end_page = args.start + args.interval - 1
        else:
            end_page = args.end
        run_gui(args.start, end_page, args.strict)
    elif args.action == 'gui2':
        run_gui2()
    elif args.action == 'gui3':
        run_gui3()
    elif args.action == 'odd_punctuation':
        run_gui4()
    elif args.action == 'fix_page_info':
        run_gui5(args.start)
    elif args.action in ('simple_clean', 'sc'):
        simple_clean()
    else:
        test()
#   process_pdfs()
#   show_headers()
#   test_garbage()
#   write_clean()
#   aspell_clean()
#   write_html()

if __name__ == '__main__':
    run()
