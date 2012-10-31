#!/usr/bin/env python
from argparse import ArgumentParser
import codecs
from collections import Counter
from ConfigParser import ConfigParser
import os
import re
import shutil
import sys

import controller
import process_pdf 
import document_builder
import line_manager
import spell_checker
import gui

def test():
    """ Whatever is being worked on."""
    """ Currently, either proper nouns or cross-line fixes."""
#   headers()
#   remove_headers()
    proper_names()
def possible_headers():
    lang = get_lang()
    dict_ = './dict.{}.pws'.format(lang)
    checker = spell_checker.AspellSpellChecker(lang, dict_)
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
    dict_ = './dict.{}.pws'.format(lang)
    checker = spell_checker.AspellSpellChecker(lang, dict_)
    db = document_builder.SpellcheckDocMaker(checker)
    db.make_line_join_doc('text/clean')

def fix_spells():
    """ Runs through the document, finds all the bad words, then 
    tries to find fixed versions of them.
    """
    lang = get_lang()
    dict_ = './dict.{}.pws'.format(lang)
    checker = spell_checker.AspellSpellChecker(lang, dict_)

    db = document_builder.SpellcheckDocMaker(checker)
    db.make_word_fix_doc('text/clean')

def run_gui(start_page, end_page):
    """ Batch cleans the pages in text/clean."""
    lang = get_lang()
    lm = line_manager.LineManager(
        spell_checker.AspellSpellChecker(lang, './dict.{}.pws'.format(lang)),
        start_page,
        end_page
        )
    lm.load('text/clean')
    gui.main(lm)
    lm.write_pages('text/clean', False)
def new():
    """ Create/update config, dictionary, and file structure."""
    # Set up pdfs
    if not os.path.exists('pdfs'):
        os.mkdir('pdfs')
        for filename in os.listdir('.'):
            print filename
            if filename.endswith('pdf'):
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
    dict_file_name = './dict.{}.pws'.format(lang)
    if not os.path.exists(dict_file_name):
        with open(dict_file_name, 'a') as f:
           f.write('personal_ws-1.1 {} 0'.format(lang)) 
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
        pdfs = [os.path.splitext(filename)[0] for filename in os.listdir('pdfs') if filename.endswith('pdf')]
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
        ('metadata', 'header', 'What is the header text of the book?'),
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
    
def clean(start_page, end_page):
    """ Batch cleans the pages in text/clean."""
    lang = get_lang()
    lm = line_manager.LineManager(
        spell_checker.AspellSpellChecker(lang, './dict.{}.pws'.format(lang)),
        start_page,
        end_page
        )

    config = ConfigParser()
    config.read('book.cnf')
    try:
        clean_headers = config.getboolean('process', 'clean_headers')
    except:
        clean_headers = True
    if clean_headers:
	print 'cleaning headers'
        remove_headers()
        if not config.has_section('process'):
            config.add_section('process')
        config.set('process', 'clean_headers', 'false')
        with open('book.cnf', 'wb') as f:
            config.write(f)
        lm.load('text/clean')
        lm.quick_fix()
    else:
        # if interrupted by keyboard, go ahead and write changes
        lm.load('text/clean')
        try:
            lm.fix_lines()
        except KeyboardInterrupt:
            pass
    lm.write_pages('text/clean', False)

def extract_images(verbose):
    pdf_processor = process_pdf.PdfProcessor(verbose)
    pdf_processor.extract_images_from_pdfs()
    pdf_processor.extract_pages_from_images()
    
def extract_text(verbose):
    lang = get_lang()
    tesseract_lang = aspell_lang_to_tesseract_lang(lang)
    pdf_processor = process_pdf.PdfProcessor(verbose)
    pdf_processor.extract_text_from_pages(tesseract_lang)

def aspell_lang_to_tesseract_lang(aspell_lang):
    if aspell_lang.startswith('fr'):
        return 'fra'
    else:
    # default English
        return 'eng'

def aspell_clean():

    starts_with_cap = re.compile('^[A-Z]')
    lang = get_lang()
    dict_ = './dict.{}.pws'.format(lang)
    checker = spell_checker.AspellSpellChecker(lang, dict_)
    bad_word_ctr = Counter()
    for fn in os.listdir('text/clean'):
        if fn.endswith('.txt'):
            for bad_word in checker.check_document('text/clean/{}'.format(fn)):
                bad_word_ctr[bad_word] += 1
    for bad_word, count in bad_word_ctr.most_common():
        if not starts_with_cap.match(bad_word):
            continue
        print '{:>3}: {}'.format(count, bad_word)
        print 'Add to dictionary? (y)es, (n)o, (q)uit'
        sys.stdout.write('> ')
        result = raw_input()
        if result.lower().startswith('y') or result.lower().startswith('a'):
            with codecs.open(dict_, mode='ab', encoding='utf-8') as f:
                f.write(bad_word)
                f.write('\n')
        elif result.lower().startswith('q'):
            break
        
def aspell_run(start, end):
    lang = get_lang()
    dict_ = './dict.{}.pws'.format(lang)
    checker = spell_checker.AspellSpellChecker(lang, './dict.{}.pws'.format(lang))
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
    actions = {
        'new': 'n',
        'extract_all': 'e',
        'extract_images': 'i',
        'extract_text': 't',
        'spell_check': 'a',
        'interactive_spell_check': 'p',
        'clean': 'c',
        'fix': 'f',
        'html': 'h',
        'gui': 'g',
        'fix_spells': 'fs',
        'test': 't',
    }
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
        default=10,
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

    args = parser.parse_args()
    acceptable_actions = [item for pair in actions.items() for item in pair]
    if args.action not in acceptable_actions:
        print 'Interactive mode not ready yet. Please try:'
        print ', '.join(actions.keys())
    elif args.action in ('new', 'n',):
        new()
    elif args.action in ('extract_all', 'e',):
        extract_images(args.verbose)
        extract_text(args.verbose)
    elif args.action in ('extract_images', 'i',):
        extract_images(args.verbose)
    elif args.action in ('extract_text', 't',):
        extract_text(args.verbose)
    elif args.action in ('spell_check', 'a',):
        aspell_clean()
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
    elif args.action in ('fix_spells', 'ft',):
        fix_spells()
        cross_line_fixes()
    elif args.action in ('html', 'h',):
        print '"HTML" is not ready yet'
    elif args.action in ('gui', 'g'):
        if args.end == 0:
            end_page = args.start + args.interval - 1
        else:
            end_page = args.end
        run_gui(args.start, end_page)
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
