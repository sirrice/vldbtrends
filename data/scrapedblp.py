import requests
import pyquery


def get_me_unicode(v):
  if isinstance(v, unicode): 
    s = v.encode('utf-8', errors='ignore')
  elif isinstance(v, basestring): 
    s = unicode(v, 'utf-8', errors='ignore').encode('utf-8', errors='ignore')
  return s


def dl(year):
  suffix = str(year)[-2:]
  url = "http://www.informatik.uni-trier.de/~ley/db/conf/vldb/vldb%s.html" % suffix
  r = requests.get(url)
  pq = pyquery.PyQuery(r.content)
  titles = pq.find(".title")
  text = '\n'.join([get_me_unicode(pq(t).text()) for t in titles[1:]])

  with file("./vldb%s.txt" % year, 'w') as f:
    f.write(text)

for year in range(1975, 1999):
  dl(year)