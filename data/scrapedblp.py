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
    url = self.url % suffix
    r = requests.get(url)
    pq = pyquery.PyQuery(r.content)
    titles = pq.find(".title")
    text = '\n'.join([get_me_unicode(pq(t).text()) for t in titles[1:]])

    with file("%s/%s%s.txt" % (self.outdir, self.conf, year), 'w') as f:
      f.write(text)


if __name__ == '__main__':
  scraper = Scraper("chi", "http://www.informatik.uni-trier.de/~ley/db/conf/chi/chi%s.html", './data/')
  for year in range(2000, 2014):
    scraper(year)