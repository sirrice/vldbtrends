import math
import sqlite3
from util import Canonicalizer


canonicalize = Canonicalizer()
db = sqlite3.connect('stats.db')
db.create_function("log", 1, math.log)

def block_iter(l, nblocks=2):
    """
    partitions l into nblocks blocks and returns generator over each block
    @param l list
    @param nblocks number of blocks to partition l into
    """
    blocksize = int(math.ceil(len(l) / float(nblocks)))
    i = 0
    while i < len(l):
        yield l[i:i+blocksize]
        i += blocksize      


spark = """<div class='row trend' style='height: 30px'>
<div class='span1 word'>%s</div>
<div class='span2' style='height: 30px'><span class='spark'>%s</span></div></div>"""





def consistent_top():
  best = None
  years = [r for r, in db.execute('select distinct year from counts order by year desc')]
  for year in years:
    q = "select word, sum(c) as s from counts where year = ? group by word order by s desc limit 10"
    cur = db.execute(q, (year,))
    words = [word for word, c in cur]

    if best:
      best.intersection_update(set(words))
    else:
      best = set(words)
  print best

def best_ratio(year, exclude_words=[], limit=4):
  q = """select counts.word,
          (((select avg(c2.c) from counts as c2 where c2.word = counts.word and c2.year > ?)) /
            ((select avg(c3.c) from counts as c3 where c3.word = counts.word and c3.year <= ?)+1)) as r
        from counts where not (counts.word in (%s))
        group by counts.word
        having r > 1
        order by r desc limit %s 
      """ % (','.join(['?'] * len(exclude_words)), limit)
  return [(w,r) for w,r in db.execute(q, tuple([year, year] + exclude_words) )]


def word_counts(word):
  q = "select year, sum(c) from counts where word like '%%%s%%' group by year order by year" % word
  cur = db.execute(q)
  cs = [c for y,c in cur]
  return cs

def render_words(words, blocksize=2):
  maxc = 0
  html = []
  for block in block_iter(words, blocksize):
      html.append("<div class='span3'>")
      for word in block:
        cs = word_counts(word)
        html.append( spark % (word, ','.join(map(str, cs))) )
        if cs:
          maxc = max(maxc, max(cs))
      html.append("</div>")
  html = ''.join(html)        
  return html





maxc = 0



q = """select counts.word, (avg(c))/(1+(1+max(c))-(min(c)+1))  as r
       from counts 
       group by counts.word
       order by r desc limit 9
    """
words = [r[0] for r in db.execute(q)]
stable = render_words(words, 3)



q = """select counts.word, max(c)/(min(c)+1) as r
       from counts 
       where (select year from counts as c2 where c2.word = counts.word order by c desc, year asc limit 1)  > (select year from counts as c3 where c3.word = counts.word order by c asc, year desc limit 1) and (select year from counts as c2 where c2.word = counts.word order by c desc, year asc limit 1) > 2008
       group by counts.word
       order by r desc limit 12
    """
words = [r[0] for r in db.execute(q)]
hot = render_words(words, 3)



q = """select counts.word, max(c)/(min(c)+1) as r
       from counts 
       where (select year from counts as c2 where c2.word = counts.word order by c desc, year asc limit 1) < (select year from counts as c3 where c3.word = counts.word order by c asc, year asc limit 1)
       group by counts.word
       order by r desc limit 12
    """
words = [r[0] for r in db.execute(q)]
cold = render_words(words, 3)




ratios = []
for year in range(2010, 2013):
  ratios += best_ratio(year, [], 10)
ratios.sort(key=lambda p: p[1], reverse=True)
words = []
for w,r in ratios:
  if w not in words:
    words.append(w)

html2 = render_words(words[:15], 3)

topk = """<table class='topk'>
	<tr><td class='year' colspan=2>%s</td></tr>
    %s
   </table>
"""    
topkrow = "<tr><td class='word'>%s</td><td class='count'>%s</td></tr>"

years = [r for r, in db.execute('select distinct year from counts order by year desc')]
html3 = []
for block in block_iter(years, 3):
    for year in block:
        q = "select word, sum(c) as s from counts where year = ? group by word order by s desc limit 10"
        cur = db.execute(q, (year,))
        rows = []
        for word, c in cur:
            rows.append(topkrow % (word, c))
        html3.append(topk % (year, ''.join(rows)))
    html3.append("	<div style='clear:both'>")
html3 = ''.join(html3)


mywords = canonicalize(['provenance', 'visualization', 'mining', 'bigdata'])
html4 = render_words(mywords, 4)

template = file('template.html', 'r').read()

print template % (stable, hot, cold, html2, html3, html4)

db.close()


