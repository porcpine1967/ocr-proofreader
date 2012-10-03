#!/usr/bin/env python

from argparse import ArgumentParser
from ConfigParser import ConfigParser
import os
import shutil
import sys
import Image

import matplotlib.pyplot as plt


class ImageAnalyzer(object):

    def __init__(self, path_to_image):
        im = Image.open(path_to_image)
        image_file_name = os.path.basename(path_to_image)
        self.image_file_base, ext = os.path.splitext(image_file_name)
        self.rows, self.columns = self.rows_and_columns(im)

    def rows_and_columns(self, im):
        """ Returns the pixel values of an image
        divided into two multidimensional arrays."""
    
        width, height = im.size
        rows = []
        current_row = None
        for index, pixel in enumerate(im.getdata()):
            if not index % width:
                current_row = []
                rows.append(current_row)
            current_row.append(pixel)
 
        columns = [[] for i in xrange(width)]
        for row in rows:
            for index, pixel in enumerate(row):
                columns[index].append(pixel)
        return rows, columns

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
        
    def text_columns(self, ):
        """ Divides the image into strips divided by whitespace
        (within sensitivity pixels of being a pure white column).
        returns the x boundaries of the columns in descending order
        of width."""
        inked_blocks = []

        first_black_column = -1
        last_black_column = -1

        for index, column in enumerate(self.columns):
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
        return sorted(inked_blocks, reverse=True, key=lambda x: x[1] - x[0])
        
    def graph(self):
        plt.close('all')
        column_avgs = [255 - (sum(column)/len(column)) for column in self.columns]
        plt.plot(xrange(len(self.columns)), column_avgs, 'b-')
        plt.savefig('{}.png'.format(self.image_file_base))
class PageCropException(Exception):
    pass

class PageCropper(object):
    """ Takes a scanned image of two pages and 
    crops them into two text areas.
    """
    def __init__(self, max_non_white_ctr=20, verbose=False):
        self.max_non_white_ctr = max_non_white_ctr
	self.verbose = verbose

    def white_borders(self, pixel_lists, start_index, end_index):
        borders = []
        non_white_ctr = 0
        in_white = False
        for index, pixel_list in enumerate(pixel_lists):
            white = sum(pixel_list[start_index:end_index + 1])/(end_index + 1 - start_index) > 245
            if white and not in_white:
                in_white = True
                # first border should be from white to text
		if borders:
                    borders.append(index)
            elif in_white and not white:
                non_white_ctr += 1
                if non_white_ctr >= self.max_non_white_ctr:
                    borders.append(index - non_white_ctr)
                    in_white = False
                    non_white_ctr = 0
            elif in_white and white:
                non_white_ctr = 0
        return borders
    def vertical_white_borders(self, columns):
        """ Returns array of transitions between white and non-white areas.

        Should result in 6 numbers:
        last white column before text of page one starts
        first white column after text of page one ends
        last white column before fuzzy line between pages
        first white column after fuzzy line between pages
        last white column before text of page two starts
        first white column after text of page two ends
        """ 
        return self.white_borders(columns, 0, len(columns[0]) - 1)

    def horizontal_white_borders(self, rows, start_index, end_index):
        """ Called for each page so fuzzy line between pages not included."""
        return self.white_borders(rows, start_index, end_index)

    def crop(self, path_to_image, destination_dir):
        """ Split image into two text areas and save to destiniation dir.

        New images will have same name as original with '-a' and '-b' placed
        before extension."""
        im = Image.open(path_to_image)
        ia = ImageAnalyzer(path_to_image)
        text_blocks = ia.text_columns()
        if text_blocks[0][0] < text_blocks[1][0]:
            page_one_x_start, page_one_x_end = text_blocks[0]
            page_two_x_start, page_two_x_end = text_blocks[1]
        else:
            page_two_x_start, page_two_x_end = text_blocks[0]
            page_one_x_start, page_one_x_end = text_blocks[1]
        imagename = os.path.basename(path_to_image)
        imagename_base, image_ext = os.path.splitext(imagename)
        # page one 
        page_one_horizontal_borders = self.horizontal_white_borders(ia.rows, page_one_x_start, page_one_x_end) 
        page_one_y_start = 0#page_one_horizontal_borders[0]
        page_one_y_end = im.size[1] #page_one_horizontal_borders[-1]
        page_one = im.crop((page_one_x_start -5, page_one_y_start, page_one_x_end + 5, page_one_y_end,))
        page_one.save('{}/{}-a{}'.format(destination_dir, imagename_base, image_ext))
	if self.verbose:
            print '{}-a saved'.format(imagename_base)
        # page two 
        page_two_horizontal_borders = self.horizontal_white_borders(ia.rows, page_two_x_start, page_two_x_end) 
        page_two_y_start = 0#page_two_horizontal_borders[0]
        page_two_y_end = im.size[1] #page_two_horizontal_borders[-1]
        page_two = im.crop((page_two_x_start - 5, page_two_y_start, page_two_x_end + 5, page_two_y_end,))
        page_two.save('{}/{}-b{}'.format(destination_dir, imagename_base, image_ext))
	if self.verbose:
            print '{}-b saved'.format(imagename_base)

class PdfProcessor(object):
    def __init__(self, verbose=False):
        self.project_path = os.path.abspath('.')
        self.config = ConfigParser()
        self.config.read('book.cnf')
        self.page_cropper = PageCropper(20, verbose=verbose)
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
        os.chdir('{}/images/raw'.format(self.project_path))
        for root, dirs, files in os.walk('.'):
            destination_dir = '{}/images/cropped/{}'.format(self.project_path, root)
            os.makedirs(destination_dir)
            for f in files:
                if self.verbose:
                    print 'extracting pages from {}'.format(f)
                source_file = '{}/images/raw/{}/{}'.format(self.project_path, root, f)
                try:
                    self.page_cropper.crop(source_file, destination_dir)
                except (PageCropException, IndexError) as e:
                    if self.verbose:
                        print ' FAIL', e
                    if not os.path.exists('fail_crop'):
                        os.makedirs('fail_crop')
                    shutil.move(source_file, 'fail_crop')
        os.chdir(self.project_path)

    def setup(self):
        if not os.path.exists(self.destination_dir):
            os.makedirs('{}/images'.format(self.destination_dir))
    
    def extract_images_from_pdfs(self):
        os.chdir(self.project_path)
        for full_filename in os.listdir('pdfs'):
            os.chdir(self.project_path)
            if full_filename.endswith('pdf'):
                filename, ext = os.path.splitext(full_filename)
                working_dir = 'images/raw/{}'.format(filename)
                os.makedirs(working_dir)
                shutil.copy('pdfs/{}'.format(full_filename), working_dir)
                os.chdir(working_dir)
                os.system('pdfimages {} {}'.format(full_filename, filename))
                os.remove(full_filename)
        os.chdir(self.project_path)

    def extract_text_from_pages(self, lang='eng'):
        os.chdir('{}/images/cropped'.format(self.project_path))
        linked_images_dir = os.path.abspath('{}/images/pages/'.format(self.project_path))
        os.makedirs(linked_images_dir)
        raw_destination_dir = '{}/text/raw/'.format(self.project_path)
        os.makedirs(raw_destination_dir)
        clean_destination_dir = '{}/text/clean/'.format(self.project_path)
        os.makedirs(clean_destination_dir)
        current_page = self.config.getint('extract_text', 'start_page_number')
        ignores = self.config.get('extract_text', 'ignore_pages').split()
        for root in self.config.get('extract_text', 'ordered_dirnames').split():
            for f in  sorted(os.listdir(root)):
                source_file = '{}/{}'.format(root, f)
                if source_file in ignores:
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

if __name__ == '__main__':
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
