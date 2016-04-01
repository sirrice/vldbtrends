import click
import sqlite3
import os
import re
from util import Canonicalizer
from collections import Counter, defaultdict


canonicalize = Canonicalizer()

re_bad = re.compile('[^\w\'\s]')
re_db = re.compile('data\s*base')
re_bd = re.compile('big\s*data')

def parse(db, conf, stemtoword):
    cur = db.execute("select distinct year from titles where conf = ?", (conf,))
    for year, in cur:
      counter = Counter()
      uniquetitles = set()
      ccur = db.execute("select title from titles where conf = ? and year = ?", (conf, year))
      for title, in ccur:
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

      print year, len(counter)
      yield year, counter

def put_in_sqlite(db, conf):
  stemtoword = {}
  ycounters = {}
  gcounter = Counter()
  for year, counter in parse(db, conf, stemtoword):
    gcounter.update(counter)
    ycounters[year] = counter

  for k in gcounter.keys():
    v = gcounter[k]

    if v <= 1:
      continue

    if k not in stemtoword:
      print "skipping", k
      continue
  
    for year, counter in ycounters.items():
      db.execute("insert into counts values(?, ?, ?, ?)", 
          (conf, year, stemtoword[k], counter.get(k, 0)))
    db.commit()

@click.command()
@click.argument("dbname")
@click.argument("conf")
def main(dbname, conf):
  db = sqlite3.connect(dbname)
  try:
    db.execute("create table counts (conf, year int, word text, c int)")
    db.execute("create index c_y on counts(conf, year)")
    db.execute("create index c_w on counts(conf, word)")
  except Exception as e:
    print "you are probably overwriting the database"
    pass

  put_in_sqlite(db, conf)

  db.commit()
  db.close()

if __name__ == "__main__":
  main()
