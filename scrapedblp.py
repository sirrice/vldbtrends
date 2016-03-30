import os
import requests
import pyquery

class Scraper(object):
  def __init__(self, conf, url_fmt, outdir="./"):
    self.conf = conf
    self.url = url_fmt
    self.outdir = outdir


  def get_me_unicode(self, v):
    if isinstance(v, unicode): 
      s = v.encode('utf-8', errors='ignore')
    elif isinstance(v, basestring): 
      s = unicode(v, 'utf-8', errors='ignore').encode('utf-8', errors='ignore')
    return s


  def __call__(self, year, suffix=None):
    if not suffix:
      suffix = year
    outname = "%s/%s%s.txt" % (self.outdir, self.conf, year)
    print "%s - %s" % (self.conf, year)
    if os.path.exists(outname): 
      print "skip"
      return

    url = self.url % suffix
    r = requests.get(url)
    pq = pyquery.PyQuery(r.content)
    titles = pq.find(".title")
    text = '\n'.join([self.get_me_unicode(pq(t).text()) for t in titles[1:]])
    text = text.strip()


    if text:
      with file(outname, 'w') as f:
        f.write(text)


if __name__ == '__main__':
  scraper = Scraper("chi", "http://www.informatik.uni-trier.de/~ley/db/conf/chi/chi%s.html", './data/')
  scraper = Scraper("tap", "http://dblp.uni-trier.de/db/journals/tap/tap%s.html", './data/')
  #for year in range(2000, 2014):
  for year in range(1, 14):
    scraper(year)