import pdb
import click
import sqlite3
import os
import requests
import pyquery
from parse import put_in_sqlite

class Scraper(object):
  def __init__(self, conf, url_fmt, outdir="./"):
    self.conf = conf
    self.url = url_fmt
    self.outdir = outdir
    self.db = sqlite3.connect("./words.db")
    qs = [
      "create table titles(id integer primary key, year int, conf int, title text)",
      "create table authors(tid int, name text)",
      "create table html(url text, content text)",
      "create table counts (conf, year int, word text, c int)",
      "create index c_y on counts(conf, year)",
      "create index c_w on counts(conf, word)"
    ]

    for q in qs:
      try:
        self.db.execute(q)
      except Exception as e:
        print(e)
        pass

  def close(self):
    try:
      self.db.close()
    except:
      pass

  def get_me_unicode(self, v):
    if isinstance(v, str): 
      s = v.encode('utf-8', errors='ignore')
    elif isinstance(v, str): 
      s = str(v, 'utf-8', errors='ignore').encode('utf-8', errors='ignore')
    return s.decode('unicode_escape').encode('ascii','ignore')

  def get_url(self, url):
    try:
      cur = self.db.execute("SELECT content FROM html WHERE url = ?", (url,))
      return cur.fetchone()[0]
    except:
      r = requests.get(url)
      self.db.execute("INSERT INTO html VALUES(?,?)", (url, r.content))
      return r.content


  def __call__(self, year, suffix=None):
    if not suffix:
      suffix = year

    try:
      cur = self.db.execute("""
        select count(*) from titles 
        where year = ? and conf = ?  """,
        (year, self.conf)
      )
      row = cur.fetchone()
      if row[0] > 1:
        pass
        #return
    except Exception as e:
      print(e)
      pass

    url = self.url % suffix
    print(url)
    content = self.get_url(url)
    pq = pyquery.PyQuery(content)
    title_els = pq.find(".title")

    authors = []
    titles = []
    for t in title_els[1:]:
      siblings = t.getparent().getchildren()
      idx = siblings.index(t)
      authors.append(list(filter(bool, (s.text_content().strip() for s in siblings[:idx]))))
      title = self.get_me_unicode(pq(t).text())
      titles.append(title)

    #if len(titles) == 0:
    #pdb.set_trace()
    print(("%s %d\t%d titles" % (self.conf, year, len(titles))))

    title_ids = []
    for title in titles:
      cur = self.db.execute("INSERT INTO titles(year, conf, title) values (?,?,?) RETURNING rowid",
                      (year, self.conf, title))
      row = cur.fetchone()
      title_id = row[0]
      title_ids.append(title_id)

    assert(len(title_ids) == len(authors))

    title_authors = []
    for tid, names in zip(title_ids, authors):
      for name in names:
        title_authors.append((tid, name))

    self.db.executemany("INSERT INTO authors(tid, name) values (?, ?)", title_authors)
    self.db.commit()


@click.command()
@click.argument("name")
@click.argument("urlpattern")
@click.argument("startyear", type=int)
@click.argument("start", type=int)
@click.argument("end", type=int)
def main(name, urlpattern, startyear, start, end):
  """
Some common URLs

nips "http://dblp.uni-trier.de/db/conf/nips/nips%s.html" 1987 1987 2016

chi "http://www.informatik.uni-trier.de/~ley/db/conf/chi/chi%s.html" 1989 1989 2016

vldb "http://dblp.uni-trier.de/db/conf/vldb/vldb%s.html" 1975 75 99

vldb "http://dblp.uni-trier.de/db/conf/vldb/vldb%s.html" 2000 2000 2008

vldb "http://dblp.uni-trier.de/db/journals/pvldb/pvldb%s.html" 2009 1 16
  """
  scraper = Scraper(name, urlpattern, "./data/")
  for idx, suffix in enumerate(range(start, end+1)):
    if startyear == start:
      scraper(suffix, suffix)
    else:
      scraper(startyear+idx, suffix)

  print(("parsing titles and computing counts for %s" % name))
  put_in_sqlite(scraper.db, name)
  scraper.close()


if __name__ == '__main__':
  main()

  # "eugene", "http://dblp.uni-trier.de/pers/hd/w/Wu_0002:Eugene?%s"
  # "nips", "http://dblp.uni-trier.de/db/conf/nips/nips%s.html" 1987, 2015
  # "chi", "http://www.informatik.uni-trier.de/~ley/db/conf/chi/chi%s.html"
  # "tap", "http://dblp.uni-trier.de/db/journals/tap/tap%s.html"
  # "vldb", "http://dblp.uni-trier.de/db/conf/vldb/vldb%s.html", 1975, 2008
  # "vldb", "http://dblp.uni-trier.de/db/journals/pvldb/pvldb%s.html", 1, 16
