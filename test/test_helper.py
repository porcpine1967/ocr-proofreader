#!/usr/bin/env python
import codecs
def test_expected(filename):
    """ Returns pairs of test string, expected result from a file."""
    with codecs.open(filename, mode='r', encoding='utf-8') as f:
        for l in f:
            line = l.strip()
            if not line:
                continue
            values = line.split('|')
            if len(values) == 2:
                yield values
            else:
                print u'Warning: {} not valid'.format(line)
