import click
import sqlite3
import os
import re
from util import Canonicalizer
from collections import Counter, defaultdict


canonicalize = Canonicalizer()

re_bad = re.compile('[^\w\'\s]')
res = [
    (re.compile('data\s*base'), 'database'),
    (re.compile('big\s*data'), 'bigdata'),
    (re.compile('top\s*-?\s*k'), 'topk')
  ]
bad_words = [
    [ 'front', 'matter', ':'], 
    ['invited'], 
    ['edit', ':'],
    ['officers'],
    ['letter', 'chair']
]

def parse(db, conf, stemtoword):
    cur = db.execute("select distinct year from titles where conf = ?", (conf,))
    for year, in cur:
      counter = Counter()
      uniquetitles = set()
      ccur = db.execute("select title from titles where conf = ? and year = ?", (conf, year))
      for title, in ccur:
        try:
          if type(title) != str:
            title = title.decode('utf-8')
          title = re_bad.sub(' ', title.lower())
          for pattern, replacement in res:
            title = pattern.sub(replacement, title)
          if any([all(w in title for w in words) for words in bad_words]):
            print("skpping", title)
            continue
          uniquetitles.add(title)
        except Exception as e:
          print(e)
          print("bad title:", title)
          continue


      for title in uniquetitles:
        for w in title.strip().split():
          cw = canonicalize(w)
          if cw and cw not in stemtoword:
            stemtoword[cw] = w
          if cw:
            counter.update([cw])

      print(year, len(counter))
      yield year, counter

def put_in_sqlite(db, conf):
  db.execute("delete from counts where conf = ?", (conf,))


  stemtoword = {}
  ycounters = {}
  gcounter = Counter()
  for year, counter in parse(db, conf, stemtoword):
    gcounter.update(counter)
    ycounters[year] = counter

  for k in list(gcounter.keys()):
    if gcounter[k] <= 1:
      continue

    if k not in stemtoword:
      print("skipping", k)
      continue
  
    for year, counter in list(ycounters.items()):
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
    print("you are probably overwriting the database")
    pass

  put_in_sqlite(db, conf)

  db.commit()
  db.close()

if __name__ == "__main__":
  main()
