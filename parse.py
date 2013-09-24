import sqlite3
import os
import re
from util import Canonicalizer
from collections import Counter


canonicalize = Canonicalizer()

re_bad = re.compile('[^\w\'\s]')

def parse(fname, stemtoword):
    year = int(re.search('(?P<p>\d+)', fname).groups()[0])
    counter = Counter()
    uniquetitles = set()
    
    with file(fname, 'r') as f:
        for title in f:
            title = re_bad.sub(' ', title.lower())
            title = title.replace("data base", "database")
            title = title.replace("big data", "bigdata")
            if 'front' in title and 'matter' in title and 'edit' in title:
              continue
            uniquetitles.add(title)

    for title in uniquetitles:
      for w in title.strip().split():
        cw = canonicalize(w)
        if w:
          stemtoword[w] = stemtoword.get(cw, w)
        counter.update([cw])
      #counter.update(words)

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

for k,v in gcounter.most_common():
    if v <= 1:
        break
    if k not in stemtoword:
        print "skipping", k
        continue
    
    for year, counter in ycounters.items():
        db.execute("insert into counts values(?, ?, ?)", (year, stemtoword[k], counter.get(k, 0)))
        print year, stemtoword[k], counter.get(k, 0)

db.commit()
db.close()
