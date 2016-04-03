vldbtrends
==========

Super naive conference keyword trend analysis tool.   It:

1. scrapes DBLP conference pages for paper titles by year
2. does simple stemming and computes word counts by conference year
3. clusters trends for each keyword using kmeans wit configurable number of clusters
4. generates an HTML page that visualizes the clusters and top K keywords in that cluster.


<a href="http://sirrice.github.io/vldbtrends/">See it live here</a>

Depends on

    pip install click pygg wuutils

There are three steps:

    # scrape titles from DBLP pages
    python scrapedblp.py --help

    # turn titles into word counts
    python parse.py --help

    # turn word counts into HTML pages with pictures
    python cluster.py  --help

