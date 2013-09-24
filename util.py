import nltk
from nltk.corpus import stopwords



class Canonicalizer(object):
  def __init__(self):
    self.stemmer = nltk.stem.porter.PorterStemmer()
    self.stop = set(stopwords.words('english'))
    self.stop.update(['use', 'using', 'used'])

    def make_syns():
      synonyms = [
          ['graph', 'subgraph'],
          ['crowd', 'crowdsource'],
          ['mapreduce', 'hadoop'],
          ['provenance', 'lineage']
      ]
      ret = {}
      for syns in synonyms:
        for syn in syns:
          stemmed = self.stem(syn)
          ret[stemmed] = syns[0]
      return ret
    self.synonyms = make_syns()



  def title(self, title):
    return self(title.strip().split())

  def stem(self, w):
    return self.stemmer.stem(w)

  def word(self, w):
    if w in self.stop: return None
    if len(w) <= 1: return None
    stemmed = self.stem(w.strip())
    return self.synonyms.get(stemmed, stemmed)

  def __call__(self, words):
    if isinstance(words, list):
      return filter(bool, map(self.word, words))
    else:
      return self.word(words)




