#!/usr/bin/env python

import unittest
import test.test_line_manager as lm
import test.test_process_pdf as pp
import test.test_spellcheck as sc
import test.test_document_builder as db
import test.test_comparison_manager as cm
def run():
     suite = unittest.TestLoader().loadTestsFromTestCase(db.DocumentBuilderTester)
     unittest.TextTestRunner(verbosity=1).run(suite)
     suite = unittest.TestLoader().loadTestsFromTestCase(lm.LineManagerTester)
     unittest.TextTestRunner(verbosity=1).run(suite)
     suite = unittest.TestLoader().loadTestsFromTestCase(pp.PdfProcessorTest)
     unittest.TextTestRunner(verbosity=1).run(suite)
     suite = unittest.TestLoader().loadTestsFromTestCase(sc.SpellCheckTester)
     unittest.TextTestRunner(verbosity=1).run(suite)
     suite = unittest.TestLoader().loadTestsFromTestCase(cm.ComparisonManagerTester)
     unittest.TextTestRunner(verbosity=1).run(suite)

if __name__ == '__main__':
    run()
