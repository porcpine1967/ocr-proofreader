#!/usr/bin/env python

import unittest
import os
import shutil
import sys
PATH = os.path.split(os.path.realpath(__file__))[0]

import process_pdf as process_pdf



class PdfProcessorTest(unittest.TestCase):
    def setUp(self):
        pass
    def tearDown(self):
        pass

    def test_extract_images(self):
        
        os.chdir('{}/test_extract'.format(PATH))
        try:
            shutil.rmtree('images')
        except OSError:
            pass # images already removed
        pdf_processor = process_pdf.PdfProcessor()        
        pdf_processor.extract_images_from_pdfs()
        self.assertEqual(4, len([fn for fn in os.listdir('images/raw/one')]))
        self.assertEqual(4, len([fn for fn in os.listdir('images/raw/two')]))
        shutil.rmtree('images')
    def test_crop(self):
        os.chdir('{}/test_crop'.format(PATH))
        try:
            shutil.rmtree('images/cropped')
        except OSError:
            pass # images/cropped already removed

        pdf_processor = process_pdf.PdfProcessor()        
        pdf_processor.extract_pages_from_images()
        self.assertEqual(8, len([fn for fn in os.listdir('images/cropped/one')]))
        shutil.rmtree('images/cropped')

    def test_extract_text(self):
        os.chdir('{}/test_extract_text'.format(PATH))
        try:
            shutil.rmtree('text')
            shutil.rmtree('images/pages')
        except OSError:
            pass # text already removed

        pdf_processor = process_pdf.PdfProcessor()        
        pdf_processor.extract_text_from_pages()
        extracted_list = sorted([fn for fn in os.listdir('text/raw')])
        self.assertEqual(['4.txt', '5.txt', '6.txt', '7.txt',], extracted_list)
        files_checked = []
        with open('text/raw/4.txt', 'r') as f:
            for l in f:
                self.assertEqual('knew', l.strip())
                files_checked.append('4.txt')
		break
        with open('text/raw/5.txt', 'r') as f:
            for l in f:
                self.assertEqual('a chap', l.strip())
                files_checked.append('5.txt')
		break
        with open('text/raw/6.txt', 'r') as f:
            for l in f:
                self.assertEqual('up on it', l.strip())
                files_checked.append('6.txt')
		break
        with open('text/raw/7.txt', 'r') as f:
            for l in f:
                self.assertEqual('miffed about', l.strip())
                files_checked.append('7.txt')
		break
        self.assertEqual(extracted_list, files_checked, 'missed a file')
        shutil.rmtree('text')
        shutil.rmtree('images/pages')

    def test_paragraphs(self):
        os.chdir('{}/test_paragraphs'.format(PATH))
        expected_line_count = 37
        paragraph_buffer = 20
        straight_analyser = process_pdf.ImageAnalyzer('straight.pbm')
        straight_rows = straight_analyser.text_rows()
        self.assertEqual(expected_line_count, len(straight_rows))
        paragraph_rows = [idx_row[0] for  idx_row in enumerate(straight_rows) if idx_row[1][1] > paragraph_buffer]
        slanted_analyser = process_pdf.ImageAnalyzer('slanted.pbm')
        slanted_rows = slanted_analyser.text_rows()
        self.assertEqual(expected_line_count, len(slanted_rows))
        paragraph_rows = [idx_row[0] for  idx_row in enumerate(slanted_rows) if idx_row[1][1] > paragraph_buffer]
        self.assertEqual([0, 9, 20, 23, 25, 30, 32, 33, 34, 35,], paragraph_rows)


if __name__ == '__main__':
    unittest.main()
