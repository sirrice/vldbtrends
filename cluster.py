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
  xs = np.array(list(range(minyear, maxyear+1)))

  # total words per year for normalization purposes
  r = db.execute("select year, count(*) from counts where conf=? order by year", (conf,))
  year2c = dict([(year, c) for year, c in r])
  yearcounts = dict2arr(year2c, list(range(minyear, maxyear+1)), 1)

  # papers per year 
  r = db.execute("select year, count(*) from titles where conf=? group by year order by year", (conf,))
  papersperyear = np.array([c for year, c in r])



  def add_content(subcluster, suffix):
    """
    Render the cluster as an image
    """

    fname = './plots/%s_%s.png' % (conf, suffix)

    # pick the top 10 terms
    print(subcluster)
    subcluster = sorted(subcluster, key=lambda t: max(t[1:].astype(float)), reverse=True)
    subcluster = subcluster[:10]

    words = np.array(subcluster)[:,0]
    ys = np.array(subcluster)[:,1:].astype(float)
    mean = [np.mean(ys[:,i]) for i in range(ys.shape[1])]
    maxmean = max(mean)
    idx = mean.index(maxmean)


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
    

    # this is used to make the top-k list in the HTML later
    return ['', words, fname, idx]
    #content.append((suffix, words, fname, idx))



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
      if (max([v / (1.+year2c.get(y,0)) for y, v in list(d.items())]) < .1): 
        continue

      # some years may not have the word
      counts = dict2arr(d, range(minyear, maxyear+1), 1.0)
      if max(counts) <= 2:
        continue

      #ret.append([w] + counts)
       
      # naive window averaging smoothing over the trend curve
      kernel = np.array([.25, .5, .75, 1, .75, .5, .25]) 
      kernel = np.array([.33, .33, .33])
      smooth = list(np.convolve(counts, kernel, mode='same'))
      ret.append([w] + smooth)
    return np.array(ret)


  vects = vectors()
  # dimensions: words (row) x year (col)
  data = vects[:,1:].astype(float)
  raw_data = np.copy(data)

  # Reshape the matrix to group every K years
  K = 1
  data_reshaped = data.reshape((data.shape[0], -1, K))

  # Sum along the second axis (axis=1) to get the sum of every group of 5 columns
  data = np.mean(data_reshaped, axis=2)


  # there's a bajillion ways to normalize the counts before clustering.
  # we do the following:

  # 1. divide by the number of papers that year
  for idx in range(data.shape[1]):
    data[:,idx] /= float(papersperyear[idx])**.25


  # 1. divide by the total number of words in that year
  #    (normalize by column)
  #for idx in range(data.shape[1]):
  #  data[:,idx] /= float(max(data[:,idx]))

  # 3a. compute log(mean+1) so volume is a contributing factor
  #volume = np.array([[math.log(max(l)+1.)]*len(l) for l in data])

  # 2. ensure zero mean and 1 std
  #    (normalize by row)
  #data = np.array([(l - np.mean(l)) / (max(l)) for l in data ])


  # 3b. add back log(mean+1) so volume is a contributing factor
  #data += volume


  content = []
  all_words = vects[:,0]
  if 1:

    # for each year, find the top words
    year_word_indexes = []
    for year in range(data.shape[1]):
      min_counts = np.min(data, axis=1)
      max_counts = np.max(data, axis=1)
      max_indices = np.argmax(data, axis=1)
      bool_idxs = max_indices == year

      good_indices = []

      for word_index, (min_count, max_count, max_index) in enumerate(zip(min_counts, max_counts, max_indices)):
        if max_index != year: continue
        counts = data[word_index,:]
        thresh = min_count + (0.90 * (max_count-min_count))

        if (all(counts[max(0,year-5):year-1] <= thresh) and 
            all(counts[year+2:year+10] <= thresh)):
          good_indices.append(word_index)


      year_word_indexes.append(good_indices)

    # accumulate years until there's ~10 words in the buffer and make that a cluster

    years = []
    buffer = set()
    for year, good_indices in enumerate(year_word_indexes):
      years.append(year)
      buffer.update(good_indices)
      if len(years) < 10:
        if len(buffer) < 10 and year < len(year_word_indexes)-1: continue

        counts = np.array([max(raw_data[i,years]) for i in buffer])
        if len(counts) == 0: continue
        if sum(counts > (max(counts) * 0.2)) < 8 and year < len(year_word_indexes)-1: continue

      if len(buffer) == 0: 
        print("buffer empty, years:", years)
        continue


      good_indices = list(buffer)
      raw_subset = raw_data[good_indices]#bool_idxs]
      words = vects[good_indices,0]
        
      weightf = lambda i: max([raw_subset[i,y] / (np.sum(raw_data[:,y])**.5) for y in years])
      idxs = list(range(len(words)))
      idxs = sorted(idxs, key=weightf, reverse=True)
      sorted_counts = np.array([max(raw_subset[i,years]) for i in idxs])
      sorted_words = np.array([words[i] for i in idxs])
      mask = (sorted_counts > 1) & (sorted_counts > (max(sorted_counts) * 0.2))
      mask |= np.array(range(len(sorted_counts))) < 10
      sorted_counts = sorted_counts[mask]
      sorted_words = sorted_words[mask]
      print(year, sorted_words[:10], sorted_counts[:10])

      idxs = [np.where(all_words == word)[0][0] for word in sorted_words]
      print(idxs)
      cluster = vects[idxs,:].copy()
      if len(cluster) == 0: continue
      for i in range(cluster.shape[0]):
        cluster[i,0] = f"{cluster[i,0]} {int(np.max(cluster[i,1:].astype(float)))}"

      
      info = add_content(cluster, str(minyear + (year*K)))
      if len(years) == 1:
        info[0] = str(minyear + K*years[0])
      else:
        info[0] = f"{minyear + K * min(years)} - {minyear + K * max(years)}"
      content.append(tuple(info))
      buffer = set()
      years  =[]
    
    print([c[0] for c in content])



  if 0:
    clusterer = KMeans(nclusters, n_init=50, init='k-means++')
    clusterer.fit(data) 
    labels = clusterer.labels_


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

      info = add_content(cluster, label)
      content.append(tuple(info))

    content.sort(key=lambda c: c[-1])



  # make HTML
  from jinja2 import Template
  with open('./clustertemplate.html', 'r') as f:
    template = Template(f.read())

  with open(outname, 'w') as f:
    f.write( template.render(content=content))






@click.command()
@click.argument("conf")
@click.argument("dbname")
@click.argument("outname")
@click.option("-k", default=10, help="Plot top K words in a cluster")
@click.option("-nclusters", default=8, help="Number of clusters")
def main(conf, dbname, outname, k=10, nclusters=10):
  cluster_and_render(conf, dbname, outname, nclusters=nclusters)

if __name__ == '__main__':
  main()

  #cluster_and_render('tap', 'stats.db', './tap.html')
  #cluster_and_render('vldb', 'stats.db', './vldb.html')
  #cluster_and_render('nips', 'stats.db', './nips.html')
  #cluster_and_render('sigmod', 'stats.db', './text.html')
