import click
import sqlite3
import os
import requests
import pyquery

class Scraper(object):
  def __init__(self, conf, url_fmt, outdir="./"):
    self.conf = conf
    self.url = url_fmt
    self.outdir = outdir
    self.db = sqlite3.connect("./words.db")
    try:
      self.db.execute("create table titles(id int primary key, year int, conf int, title text)")
    except Exception as e:
      print e
      pass

  def close(self):
    try:
      self.db.close()
    except:
      pass

  def get_me_unicode(self, v):
    if isinstance(v, unicode): 
      s = v.encode('utf-8', errors='ignore')
    elif isinstance(v, basestring): 
      s = unicode(v, 'utf-8', errors='ignore').encode('utf-8', errors='ignore')
    return s.decode('unicode_escape').encode('ascii','ignore')


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
        return
    except Exception as e:
      print e
      pass

    url = self.url % suffix
    r = requests.get(url)
    pq = pyquery.PyQuery(r.content)
    titles = pq.find(".title")
    titles = [self.get_me_unicode(pq(t).text()) for t in titles[1:]]
    print "%s %d\t%d titles" % (self.conf, year, len(titles))

    allargs = [ (year, self.conf, title) for title in titles ]
    self.db.executemany(
        "insert into titles(year, conf, title) values(?, ?, ?)", 
        allargs
    )
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

"http://dblp.uni-trier.de/db/conf/nips/nips%s.html" 1987 1987 2016

"http://www.informatik.uni-trier.de/~ley/db/conf/chi/chi%s.html" 1989 1989 2016

"http://dblp.uni-trier.de/db/conf/vldb/vldb%s.html" 1975 1975 2008

"http://dblp.uni-trier.de/db/journals/pvldb/pvldb%s.html" 2009 1 16
  """
  scraper = Scraper(name, urlpattern, "./data/")
  for idx, suffix in enumerate(xrange(start, end+1)):
    if startyear == start:
      scraper(suffix, suffix)
    else:
      scraper(startyear+idx, suffix)

  scraper.close()


if __name__ == '__main__':
  main()

  # "eugene", "http://dblp.uni-trier.de/pers/hd/w/Wu_0002:Eugene?%s"
  # "nips", "http://dblp.uni-trier.de/db/conf/nips/nips%s.html" 1987, 2015
  # "chi", "http://www.informatik.uni-trier.de/~ley/db/conf/chi/chi%s.html"
  # "tap", "http://dblp.uni-trier.de/db/journals/tap/tap%s.html"
  # "vldb", "http://dblp.uni-trier.de/db/conf/vldb/vldb%s.html", 1975, 2008
  # "vldb", "http://dblp.uni-trier.de/db/journals/pvldb/pvldb%s.html", 1, 16