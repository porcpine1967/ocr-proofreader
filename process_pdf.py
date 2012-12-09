#!/usr/bin/env python

from argparse import ArgumentParser
from ConfigParser import ConfigParser
import os
import shutil
import sys
import Image

import matplotlib.pyplot as plt

class ImageHeuristic(object):
    """ Analyzes images
    and provides best-guess/fallback
    for where to crop.
    """
    def __init__(self, verbose=False):
        self.verbose=verbose
        self.image_analyzers = []
        self.analyzed = False
                
    def add_image(self, image_path):
        try:
            if self.verbose:
                print 'Adding:', image_path
            self.image_analyzers.append(ImageAnalyzer(image_path))
        except PageCropException:
            print 'IGNORING BAD PAGE:', image_path
        
    def analyze(self):
        if self.verbose:
            print 'Starting to Analyze'
        pages = []
        for ia in self.image_analyzers:
            if self.verbose:
                print 'Adding info for', ia.image_file_base
                print '  width a:', ia.page_a.width
                print '  width b:', ia.page_b.width
            pages.append(ia.page_a)
            pages.append(ia.page_b)
        median_width = sorted([page.width for page in pages])[len(pages)/2]

        good_page_a_starts = []
        good_page_a_ends = []
        good_page_b_starts = []
        good_page_b_ends = []
        for ia in self.image_analyzers:
            if ia.page_a.in_bounds(median_width):
                good_page_a_starts.append(ia.page_a.start)
                good_page_a_ends.append(ia.page_a.end)
            if ia.page_b.in_bounds(median_width):
                good_page_b_starts.append(ia.page_b.start)
                good_page_b_ends.append(ia.page_b.end)
        for ia in self.image_analyzers:
            if not ia.page_a.in_bounds(median_width):
                ia.page_a.start = min(good_page_a_starts)
                ia.page_a.end = max(good_page_a_ends)
            if not ia.page_b.in_bounds(median_width):
                ia.page_b.start = min(good_page_b_starts)
                ia.page_b.end = max(good_page_b_ends)
        self.analyzed = True

    def crop_all(self, destination_dir, check_for_analysis=True):
        if not self.image_analyzers:
            return
        if check_for_analysis and not self.analyzed:
            self.analyze()
        for ia in self.image_analyzers:
            ia.crop(destination_dir, self.verbose)
        
class Page(object):
    def __init__(self, position_tuple, double_width):
        self.start, self.end = position_tuple
        self.width = self.end - self.start
        self.full_width = double_width/2.0

    def in_bounds(self, median_width):
        if self.width < self.full_width:
            return abs(median_width - self.width)/self.full_width < .01 
        else:
            raise PageCropException('Wider than half page width')

class ImageAnalyzer(object):

    def __init__(self, path_to_image):
        self.path_to_image = path_to_image
        im = Image.open(self.path_to_image)
        image_file_name = os.path.basename(path_to_image)
        self.image_file_base, self.image_ext = os.path.splitext(image_file_name)
        self.load_pages(im)

    def crop(self, destination_dir, verbose):
        im = Image.open(self.path_to_image)
        image_page_a = im.crop((self.page_a.start -5, 0, self.page_a.end + 5, self.im_height,))
        image_page_a.save('{}/{}-a{}'.format(destination_dir, self.image_file_base, self.image_ext))
	if verbose:
            print '{}-a saved'.format(self.image_file_base)
        if verbose:
            print 'Cropping {} to {} - {}'.format(self.image_file_base, self.page_b.start, self.page_b.end)
        image_page_b = im.crop((self.page_b.start -5, 0, self.page_b.end + 5, self.im_height,))
        image_page_b.save('{}/{}-b{}'.format(destination_dir, self.image_file_base, self.image_ext))
	if verbose:
            print '{}-b saved'.format(self.image_file_base)

    def load_pages(self, im):
        page_data_a, page_data_b = self.text_columns(im)
        self.page_a = Page(page_data_a, self.im_width)
        self.page_b = Page(page_data_b, self.im_width)

    def columns(self, im):
        self.im_width, self.im_height = im.size
        
        columns = [[] for i in xrange(self.im_width)]
        for index, pixel, in enumerate(im.getdata()):
            columns[index % self.im_width].append(pixel)
        return columns

    def text_rows(self):
        """ Returns an array of tuples that define individual rows of text.

        tuple: (x-start, y-start, x-end, y-end)
        """
        rows = []
        first_black_row = -1
        last_black_row = -1
        current_row = []
        for idx, row in enumerate(self.rows):
            avg = sum(row)/len(row)
            if avg < 251:
                if first_black_row == -1:
                    first_black_row = idx
                last_black_row = idx
                current_row.append(row)
            else:
                if last_black_row - first_black_row > 10:
                    rows.append((first_black_row, last_black_row, current_row,))
                current_row = []
                first_black_row = -1
                last_black_row = -1
        full_tuples = []
        for fbr, lbr, row_data in rows:
            columns = [[] for i in xrange(len(row_data[0]))]

            for row in row_data:
                for index, pixel in enumerate(row):
                    columns[index].append(pixel)
            first_black_column = -1
            last_black_column = -1
            for idx, column in enumerate(columns):
                avg = sum(column)/len(column)
                if avg < 254:
                    if first_black_column == -1:
                        first_black_column = idx
                    last_black_column = idx
            full_tuples.append((fbr, first_black_column, lbr, last_black_column,))
        return full_tuples
        
    def text_columns(self, im):
        """ Divides the image into strips divided by whitespace
        (within sensitivity pixels of being a pure white column).
        returns the x boundaries of the columns in descending order
        of width."""
        inked_blocks = []

        columns = self.columns(im)
        first_black_column = -1
        last_black_column = -1

        for index, column in enumerate(columns):
            avg = sum(column)/len(column)
            if avg < 254:
                if first_black_column == -1:
                    first_black_column = index
                last_black_column = index
            else:
                if last_black_column > first_black_column > -1:
                    inked_blocks.append((first_black_column, last_black_column,))
                first_black_column = -1
                last_black_column = -1
        if len(inked_blocks) >= 2:
            return sorted(sorted(inked_blocks, reverse=True, key=lambda x: x[1] - x[0])[:2], key=lambda x: x[0])
        else:
            # something is terribly wrong with this page
            raise PageCropException('Too few columns')
        
    def graph(self):
        plt.close('all')
        column_avgs = [255 - (sum(column)/len(column)) for column in self.columns]
        plt.plot(xrange(len(self.columns)), column_avgs, 'b-')
        plt.savefig('{}.png'.format(self.image_file_base))

class PageCropException(Exception):
    pass

class PdfProcessor(object):
    def __init__(self, verbose=False):
        self.project_path = os.path.abspath('.')
        self.config = ConfigParser()
        self.config.read('book.cnf')
        self.verbose = verbose

    def fix(self):
        os.chdir('{}/fail_crop'.format(self.destination_dir))
        self.extract_pages_from_images()
        self.extract_text_from_pages()

        for f in os.listdir('.'):
            if f.endswith('.txt'):
                shutil.move(f, '..')

    def process(self, lang='eng'):
	if self.verbose:
            print 'extracting images from {}'.format(self.path_to_pdf)
        # note: this function has side effect of 
        # putting os in working directory
        self.extract_images_from_pdf()
	if self.verbose:
            print 'extracting pages from images'
        self.extract_pages_from_images()
        self.extract_text_from_pages(lang)

    def extract_pages_from_images(self):
        source_dir = '{}/images/raw'.format(self.project_path)
        if self.verbose:
            print 'Starting to extract pages from "{}"'.format(source_dir)
        for root, dirs, files in os.walk(source_dir):
            if not files:
                continue
            image_heuristic = ImageHeuristic(verbose=self.verbose)
            destination_dir = root.replace('/raw/', '/cropped/')
            maybe_make_dir(destination_dir)
            if self.verbose:
                print 'Adding files from', root
            for f in files:
                source_file = '{}/{}'.format(root, f)
                image_heuristic.add_image(source_file)
            image_heuristic.crop_all(destination_dir)

    def setup(self):
        if not os.path.exists(self.destination_dir):
            maybe_make_dir('{}/images'.format(self.destination_dir))
    
    def extract_images_from_pdfs(self):
        os.chdir(self.project_path)
        for full_filename in os.listdir('pdfs'):
            os.chdir(self.project_path)
            if full_filename.endswith('pdf'):
                filename, ext = os.path.splitext(full_filename)
                working_dir = 'images/raw/{}'.format(filename)
                maybe_make_dir(working_dir)
                shutil.copy('pdfs/{}'.format(full_filename), working_dir)
                os.chdir(working_dir)
                os.system('pdfimages {} {}'.format(full_filename, filename))
                os.remove(full_filename)
        os.chdir(self.project_path)

    def extract_text_from_pages(self, lang='eng'):
        os.chdir('{}/images/cropped'.format(self.project_path))
        linked_images_dir = os.path.abspath('{}/images/pages/'.format(self.project_path))
        maybe_make_dir(linked_images_dir)
        raw_destination_dir = '{}/text/raw/'.format(self.project_path)
        maybe_make_dir(raw_destination_dir)
        clean_destination_dir = '{}/text/clean/'.format(self.project_path)
        maybe_make_dir(clean_destination_dir)
        current_page = self.config.getint('extract_text', 'start_page_number')
        ignores = self.config.get('extract_text', 'ignore_pages').split()
        for root in self.config.get('extract_text', 'ordered_dirnames').split():
            for f in sorted(os.listdir(root)):
                source_file = '{}/{}'.format(root, f)
                if f in ignores or source_file in ignores:
                    continue
                basename, ext = os.path.splitext(f)
                command = 'tesseract {} {} -l {}'.format(source_file, current_page, lang)
                if self.verbose:
                    print command
                os.system(command)
                os.symlink(os.path.abspath(source_file), '{}/{}.pbm'.format(linked_images_dir, current_page))
                shutil.copy('{}.txt'.format(current_page), clean_destination_dir)
                shutil.move('{}.txt'.format(current_page), raw_destination_dir)
                current_page += 1
        os.chdir(self.project_path)

    def symlink_images(self):
        linked_images_dir = os.path.abspath('{}/images/pages/'.format(self.project_path))
        maybe_make_dir(linked_images_dir)
        current_page = self.config.getint('extract_text', 'start_page_number')
        ignores = self.config.get('extract_text', 'ignore_pages').split()
        for root_name in self.config.get('extract_text', 'ordered_dirnames').split():
            root = '{}/images/cropped/{}'.format(self.project_path, root_name)
            for f in sorted(os.listdir(root)):
                source_file = '{}/{}'.format(root, f)
                if f in ignores or source_file in ignores:
                    continue
                basename, ext = os.path.splitext(f)
                os.symlink(os.path.abspath(source_file), '{}/{}.pbm'.format(linked_images_dir, current_page))
                current_page += 1
        os.chdir(self.project_path)

def maybe_make_dir(dir_):
    try:
        os.makedirs(dir_)
    except OSError:
        pass

def run():
    parser = ArgumentParser(description="Converts pdf scans to text")
    parser.add_argument('pdf', type=str, help='Path to PDF')
    parser.add_argument('-d', type=str, dest="dest_dir", default='.',
                    help='Destination Directory (where the text files end up')
    parser.add_argument('-dpi', type=int, dest="dpi", default=200,
                    help='Dots per inch of scan')
    parser.add_argument('-fix', type=bool, dest="fix", default=False,
                    help='Run after manually fixing failures')
    parser.add_argument('-l', type=str, dest="lang", default='eng',
                    help='language code for ocr')
    args = parser.parse_args()

    pdf_processer = PdfProcessor(args.pdf, args.dest_dir, args.dpi, args.lang)
    if args.fix:
        pdf_processer.fix()
    else:
        pdf_processer.process()
if __name__ == '__main__':
#   run()
    ih = ImageHeuristic('.')
    for fn in os.listdir('.'):
        ih.add_image(fn)
    ih.analyze()
