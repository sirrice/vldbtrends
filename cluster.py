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

def dict2arr(d, keys, default=0):
  """
  d is a dictionary 
  keys is a list of keys that we want the values for
  """
  return [d.get(k, default) for k in keys]

def cluster_and_render(conf, dbname, outname="./text.html", nclusters=8):
  """
  Normalize keyword counts, cluster using kmeans, generate PNGs and HTML webpage
  """


  db = sqlite3.connect(dbname)
  r = db.execute("select min(year), max(year) from counts where conf=?", (conf,))
  minyear, maxyear = r.fetchone()

  # total words per year for normalization purposes
  r = db.execute("select year, count(*) from counts where conf=? order by year", (conf,))
  year2c = dict([(year, c) for year, c in r])
  yearcounts = dict2arr(year2c, range(minyear, maxyear+1), 1)


  def add_content(subcluster, content, suffix):
    """
    Render the cluster as an image
    """

    fname = './plots/%s_%s.png' % (conf, suffix)

    # pick the top 10 terms
    subcluster = sorted(subcluster, key=lambda t: max(t[1:].astype(float)), reverse=True)
    subcluster = subcluster[:10]

    words = np.array(subcluster)[:,0]
    ys = np.array(subcluster)[:,1:].astype(float)
    mean = [np.mean(ys[:,i]) for i in xrange(ys.shape[1])]
    maxmean = max(mean)
    idx = mean.index(maxmean)

    # this is used to make the top-k list in the HTML later
    content.append(('', words, fname, idx))


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

    # add a line for the mean
    for x, y in enumerate(mean):
      data.append(dict(group="aggregate", word='___mean___', x=xs[x], y=y, alpha=1))

    if 1:
      maxy = max(10, max(pluckone(data, 'y')))
      if maxy <= 10:
        breaks = [0, 5, 10]


    # pygg lets you write ggplot2 syntax in python
    p = ggplot(data, aes(x='x', y='y', group='word', color='group', alpha='alpha'))
    p += geom_line(size=1)
    p += scale_color_manual(values="c('normal' = '#7777dd','aggregate' = 'black')", guide="FALSE")
    p += scale_alpha_continuous(guide="FALSE")
    if 1:
      if maxy <= 10:
        p += scale_y_continuous(lim=[0, maxy], breaks=breaks, labels = "function (x) as.integer(x)")
      else:
        p += scale_y_continuous(lim=[0, maxy], labels = "function (x) as.integer(x)")
    p += legend_bottom
    p += theme(**{
      "axis.title":element_blank()
      })
    ggsave(fname, p, width=10, height=4, libs=['grid'])
    


  def vectors():
    """
    Extract a matrix of term count vectors

    Return: [
      [word, count1, count2, ...],
      ...
    ]
    """
    r = db.execute("select word, year, c from counts where conf=? order by word, year", (conf,))
    vects = defaultdict(dict)
    for w,y,c in r:
      l = vects[w]
      l[y] = float(c) 


    ret = []
    for w in vects:
      d = vects[w]

      # if word is super uncommon, skip it
      if (max(d.values()) <= 3):
        continue
      if (max([v / (1.+year2c.get(y,0)) for y, v in d.items()]) < .1): 
        continue

      # some years may not have the word
      counts = dict2arr(d, xrange(minyear, maxyear+1), 1.0)

       
      # naive window averaging smoothing over the trend curve
      smooth = []
      for i in xrange(len(counts)):
        smooth.append(np.mean(counts[max(0,i-2):i+2]))
      if max(smooth) > 2:
        ret.append([w] + smooth)
    return np.array(ret)


  vects = vectors()
  # dimensions: words (row) x year (col)
  data = vects[:,1:].astype(float)

  # there's a bajillion ways to normalize the counts before clustering.
  # we do the following:

  # 1. divide by the total number of words in that year
  #    (normalize by column)
  for idx, base in enumerate(yearcounts):
    data[:,idx] /= float(base)

  # 2. ensure zero mean and 1 std
  #    (normalize by row)
  data = np.array([(l - np.mean(l)) / (max(l)) for l in data ])


  clusterer = KMeans(nclusters, n_init=50, init='k-means++')
  clusterer.fit(data) 
  labels = clusterer.labels_
  xs = np.array(range(minyear, maxyear+1))

  content = []

  # each label is a cluster
  for label in set(labels):
    idxs = labels == label
    cluster = vects[idxs]

    # sort the words/clusters by their max count
    cluster = sorted(cluster, key=lambda t: max(t[1:].astype(float)), reverse=True)
    if not len(cluster): continue
    cluster = np.array(cluster)
    words = cluster[:,0]
    words = list(words)

    add_content(cluster, content, label)

  content.sort(key=lambda c: c[-1])



  # make HTML
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
