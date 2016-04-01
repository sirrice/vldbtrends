import click
import math
import sqlite3
import sklearn
import numpy as np
import pdb

from sklearn.cluster import KMeans
from util import Canonicalizer
from collections import *
import random

from pygg import *
from wuutils import *


def cluster_and_render(conf, dbname, outname="./text.html", nclusters=8):
  db = sqlite3.connect(dbname)
  r = db.execute("select min(year), max(year) from counts where conf=?", (conf,))
  minyear, maxyear = r.fetchone()

  def vectors():
    r = db.execute("select word, year, c from counts order by word, year")
    vects = defaultdict(dict)
    for w,y,c in r:
      l = vects[w]
      l[y] = c


    ret = []
    for w in vects:
      d = vects[w]
      counts = [float(d.get(y, 0.)) for y in xrange(minyear, maxyear+1)]
      smooth = []
      for i in xrange(len(counts)):
        smooth.append(np.mean(counts[max(0,i-1):i+2]))
      if max(smooth) > 2:
        ret.append([w] + smooth)
    return np.array(ret)


  vects = vectors()
  clusterer = KMeans(nclusters, n_init=50, init='k-means++')
  data = vects[:,1:].astype(float)
  data = np.array([((l+1.) / (1.+max(l)))**2 for l in data ])
  clusterer.fit(data) # words x year
  labels = clusterer.labels_
  xs = np.array(range(minyear, maxyear+1))

  content = []

  def add_content(subcluster, content, suffix):
    fname = './plots/%s_%s.png' % (conf, suffix)

    # pick the top 10 terms
    subcluster = sorted(subcluster, key=lambda t: max(t[1:].astype(float)), reverse=True)
    subcluster = subcluster[:10]

    words = np.array(subcluster)[:,0]
    ys = np.array(subcluster)[:,1:].astype(float)
    mean = [np.mean(ys[:,i]) for i in xrange(ys.shape[1])]
    mean = [np.median(ys[:,i]) for i in xrange(ys.shape[1])]
    maxmean = max(mean)
    idx = mean.index(maxmean)
    content.append(('', words, fname, idx))


    colors = {}
    data = []
    for arr in subcluster:
      word = arr[0]
      for x, y in enumerate(map(float, arr[1:])):
        data.append(dict(
          group="normal",
          word=word,
          x=xs[x],
          y=y,
          alpha=0.3
        ))
    for x, y in enumerate(mean):
      data.append(dict(group="aggregate", word='___mean___', x=xs[x], y=y, alpha=1))

    maxy = max(10, max(pluckone(data, 'y')))
    if maxy <= 10:
      breaks = [0, 5, 10]

    p = ggplot(data, aes(x='x', y='y', group='word', color='group', alpha='alpha'))
    p += geom_line(size=1)
    p += scale_color_manual(values="c('normal' = '#7777dd','aggregate' = 'black')", guide="FALSE")
    p += scale_alpha_continuous(guide="FALSE")
    if maxy <= 10:
      p += scale_y_continuous(lim=[0, maxy], breaks=breaks, labels = "function (x) as.integer(x)")
    else:
      p += scale_y_continuous(lim=[0, maxy], labels = "function (x) as.integer(x)")
    p += legend_bottom
    p += theme(**{
      "axis.title":element_blank()
      })
    ggsave(fname, p, width=10, height=4, libs=['grid'])
    



  for label in set(labels):
    #fig, ax = plt.subplots(1, figsize=(13, 5))

    idxs = labels == label
    cluster = vects[idxs]
    cluster = sorted(cluster, key=lambda t: max(t[1:].astype(float)), reverse=True)
    cluster = filter(lambda l: sum(map(float, l[1:])) > 4, cluster)
    if not len(cluster): continue
    cluster = np.array(cluster)
    words = cluster[:,0]
    words = list(words)

    # if 'crowd' in words:
    #   data = cluster[:,1:].astype(float)
    #   data = np.array([l / max(l) for l in data])
    #   clusterer = KMeans(2)
    #   clusterer.fit(data)
    #   for newlabel in set(clusterer.labels_):
    #     idxs = clusterer.labels_ == newlabel
    #     subcluster = cluster[idxs]
    #     add_content(subcluster, content, "%s-%s" % (label, newlabel))

    #   continue


    cluster = cluster[:10]
    add_content(cluster, content, label)

  content.sort(key=lambda c: c[-1])

  from jinja2 import Template
  template = Template(file('./clustertemplate.html').read())


  with file(outname, 'w') as f:
    f.write( template.render(content=content))

@click.command()
@click.argument("conf")
@click.argument("dbname")
@click.argument("outname")
@click.option("-k", default=10, help="Plot top K words in a cluster")
@click.option("-nclusters", default=8, help="Number of clusters")
def main(conf, dbname, outname, k=10, nclusters=8):
  cluster_and_render(conf, dbname, outname, nclusters=nclusters)

if __name__ == '__main__':
  main()

  #cluster_and_render('tap', 'stats.db', './tap.html')
  #cluster_and_render('vldb', 'stats.db', './vldb.html')
  #cluster_and_render('nips', 'stats.db', './nips.html')
  #cluster_and_render('sigmod', 'stats.db', './text.html')
