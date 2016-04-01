vldbtrends
==========

Trends in VLDB title keywords

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

