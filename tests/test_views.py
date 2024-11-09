import logging
logging.basicConfig(level=logging.DEBUG)

import sys
import os

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
# Test get_views() method using the pageview API
import pywikibot
from suggestbot.utilities.page import Page


site = pywikibot.Site('en')
page = Page(site, 'Barack Obama')
print("{0} had {1} views".format(page.title(), page.get_views()))


site2 = pywikibot.Site('ar')
page2 = Page(site2, 'إيلون ماسك')
print("{0} had {1} views".format(page2.title(), page2.get_views()))
