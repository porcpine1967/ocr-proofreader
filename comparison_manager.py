#!/usr/bin/env python

import codecs
from collections import defaultdict, Counter
import os
import sys
reload(sys).setdefaultencoding('utf8')

import diff_match_patch

class ComparisonManager(object):
    def __init__(self):
        self.dmp = diff_match_patch.diff_match_patch()
        self.clean = defaultdict(lambda: []) 
        self.raw = defaultdict(lambda: [])
        self.clean_dir = 'text/clean'
        for fn in ordered_file_names(self.clean_dir):
            with codecs.open(u'{}/{}'.format(self.clean_dir, fn), mode='rb', encoding='utf-8') as f:
                for l in f:
                    self.clean[fn].append(l.strip())
        
        raw_dir = 'text/simple_clean'
        for fn in ordered_file_names(raw_dir):
            with codecs.open(u'{}/{}'.format(raw_dir, fn), mode='rb', encoding='utf-8') as f:
                for l in f:
                    self.raw[fn].append(l.strip())
        for page_nbr in self.clean.keys():
            if len(self.clean[page_nbr]) != len(self.raw[page_nbr]):
                print page_nbr
                print 'clean', len(self.clean[page_nbr])
                print 'raw', len(self.raw[page_nbr])
            
    def histogram_2(self):
        c = Counter()
        for page_nbr in self.clean.keys():
            bad_goods = self.bad_goods(page_nbr)
            for bad, good in bad_goods:
                c[u'{}|{}'.format(bad, good)] += 1
                
        for k, v in c.most_common():
            if v > 0:
                print u'{}||{}'.format(k, v)
        print sum(c.values())
    def histogram(self):
        c = Counter()
        for page_nbr in self.clean.keys():
            bad_goods = self.bad_goods(page_nbr)
            c[len(bad_goods)] += 1
            if len(bad_goods) > 100:
                print page_nbr
                
        for k, v in c.most_common():
            print '{:>7}:{:7}'.format(k, v)
    def compare_all(self):
        for fn in ordered_file_names(self.clean_dir):
            self.compare(fn)
        
    def compare(self, page_nbr):
        with codecs.open('changes.txt', mode='ab', encoding='utf-8') as f:
            f.write(u'{}\n'.format(page_nbr))
            for bad, good in self.bad_goods(page_nbr):
                f.write( u'{:20}:{}\n'.format(good, bad))

    def bad_goods(self, page_nbr):
        bad_goods = []
        for i in xrange(len(self.clean[page_nbr])):
            clean_line = self.clean[page_nbr][i]
            raw_line = self.raw[page_nbr][i]
            bad_goods.extend(find_bad(clean_line, raw_line))
        return bad_goods
        

def find_bad(line_1, line_2):
    changes = []
    
    print_set = ([' ', "'"])
    diffs = diff_match_patch.diff_match_patch().diff_main(line_1, line_2)
    last_change = None
    last_1_idx = -1
    last_2_idx = -1
    for code, string in diffs:
#       print code, string
        if last_change:
            if code == 0:
                changes.append((last_change, '',))
            elif code == 1:
                changes.append((last_change, string,))
            last_change = None
        elif code == 1 and string in print_set:
            changes.append((
                space_bounded(line_1, last_1_idx),
                # plus one because will add it later
                space_bounded(line_2, last_2_idx + 1),)
            )
        elif code == 1:
            changes.append(('', string,))

        if code == -1 and string in print_set:
            last_1_idx += len(string)
            changes.append((
                space_bounded(line_1, last_1_idx),
                space_bounded(line_2, last_2_idx),)
            )
        elif code == -1:
            last_change = string
            last_1_idx += len(string)
        elif code == 1:
            last_2_idx += len(string)
        else:
            last_2_idx += len(string)
            last_1_idx += len(string)
    if last_change:
        changes.append((last_change, '',))
    return changes

def space_bounded(line, idx):
    """ Returns the space-bound string around idx.
    If idx is a space will search beyond it in both
    directions.
    """
    front_index = 0
    back_index = len(line)
    for i in xrange(len(line)):
        if i < idx and line[i] == ' ':
            front_index = i
        elif i > idx and line[i] == ' ':
            back_index = i
            break
    return line[front_index:back_index].strip()
        
def ordered_file_names(dir_):
    file_names = []
    for fn in os.listdir(dir_):
        name, ext = os.path.splitext(fn)
        if ext == '.txt':
            try:
                file_names.append(int(name))
            except ValueError:
                pass
    return ['{}.txt'.format(nbr) for nbr in sorted(file_names)] 

    
