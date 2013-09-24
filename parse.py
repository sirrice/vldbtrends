import sqlite3
import os
import re
from util import Canonicalizer
from collections import Counter


canonicalize = Canonicalizer()

re_bad = re.compile('[^\w\'\s]')
re_db = re.compile('data\s*base')
re_bd = re.compile('big\s*data')

def parse(fname, stemtoword):
    year = int(re.search('(?P<p>\d+)', fname).groups()[0])
    counter = Counter()
    uniquetitles = set()
    
    with file(fname, 'r') as f:
        for title in f:
            title = re_bad.sub(' ', title.lower())
            title = re_db.sub('database', title)
            title = re_bd.sub('bigdata', title)
            if 'front' in title and 'matter' in title and 'edit' in title:
              continue
            uniquetitles.add(title)


    for title in uniquetitles:
      for w in title.strip().split():
        cw = canonicalize(w)
        if cw and cw not in stemtoword:
          stemtoword[cw] = w
        if cw:
          counter.update([cw])

    return year, counter


stemtoword = {}
ycounters = {}
gcounter = Counter()
for fname in  os.listdir('./data/'):
    if fname.startswith('vldb') and fname.endswith('.txt'):
        year, counter = parse('./data/%s' % fname, stemtoword)
        gcounter.update(counter)
        ycounters[year] = counter


db = sqlite3.connect('stats.db')
try:
  db.execute("create table counts (year int, word text, c int)")
  db.execute("create index c_y on counts(year)")
  db.execute("create index c_w on counts(word)")
except:
  print "you are probably overwriting the database"
  pass


import pdb

for k in gcounter.keys():

    v = gcounter[k]

    if v <= 1:
        continue

    if k not in stemtoword:
        print "skipping", k
        continue
    
    for year, counter in ycounters.items():
        db.execute("insert into counts values(?, ?, ?)", (year, stemtoword[k], counter.get(k, 0)))
        #print year, stemtoword[k], counter.get(k, 0)

db.commit()
db.close()
