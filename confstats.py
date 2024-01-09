from sqlalchemy import *
from sqlalchemy.sql import text


for year in range(2017, 2024):
  q = f"""
  with tmp as (
  select year, name, count(distinct tid) as c from authors, titles 
  where titles.id = authors.tid and conf = 'sigmod' and year = {year} 
  group by year, name 
  having count(distinct tid) >= 3
  order by count(distinct tid) )
  SELECT * from tmp
  """

  db = create_engine("sqlite:///words.db")
  with db.connect() as conn:
    cur = conn.execute(text(q))
    data = []
    for row in cur:
      print(f"{row[0]}\t{row[2]}\t{row[1]}")



exit()



q = """ 
WITH jj as (SELECT * FROM titles, authors where titles.id = authors.tid),


auth as (select conf, year, name, count(distinct title) as c
from jj
group by conf, year, name),

paper as (select conf, year, title, count(distinct name) as c
FROM jj
group by conf, year, title),

totals as (select conf, year, count(distinct title) as papers, count(distinct name) as uniqauth, count(name) as totalauth
from jj
GROUP BY conf, year),

app as (
SELECT conf, year, substr(avg(c),1,5) as avgapp, max(c) as maxapp 
FROM paper
GROUP BY conf, year),

ppa as (
SELECT conf, year, substr(avg(c),1,5) as avgppa, max(c) as maxppa
FROM auth
GROUP BY conf, year)

SELECT totals.conf, totals.year, papers, uniqauth, totalauth, avgapp, maxapp, avgppa, maxppa
FROM totals, app, ppa
WHERE totals.conf = app.conf and totals.conf = ppa.conf and
      totals.year = app.year and totals.year = ppa.year and
      totals.year < 2024
;
"""

db = create_engine("sqlite:///words.db")
with db.connect() as conn:
  cur = conn.execute(text(q))
  data = []
  for row in cur:
    data.append(dict(zip(cur.keys(), row)))

from pygg import *
from wuutils import *

_data = fold(data, ["papers", "uniqauth", "totalauth"])

p = (ggplot(_data, aes(x="year", y='val', color='key', group='key')) +
     geom_line() +
     facet_grid(". ~ conf") + 
     axis_labels("Year", "Counts", "continuous", "continuous") + 
     legend_bottom)
ggsave("stats_counts.png", p, width=10, height=4, scale=0.8)

p = (ggplot(_data, aes(x="year", y='val', color='key', group='key')) +
     geom_line() +
     facet_grid(". ~ conf") + 
     axis_labels("Year", "Counts (log)", "continuous", "log10") + 
     legend_bottom)
ggsave("stats_counts_log.png", p, width=10, height=4, scale=0.8)




_data = fold(data, ["avgapp", "maxapp", "avgppa", "maxppa"])

for d in _data:
  if "ppa" in d['key']:
    d['type'] = "Papers/Auth"
  elif "app" in d['key']:
    d['type'] = "Authors/Paper"
  if 'avg' in d['key']:
    d['metric'] = 'AVG'
  elif 'max' in d['key']:
    d['metric'] = 'MAX'

p = (ggplot(_data, aes(x="year", y='val', color='metric', group='metric')) +
     geom_line() +
     facet_grid("type ~ conf", scales=esc("free_y")) +
     axis_labels("Year", "Rates") + 
     legend_bottom)
ggsave("stats_per.png", p, width=10, height=4, scale=0.8)



