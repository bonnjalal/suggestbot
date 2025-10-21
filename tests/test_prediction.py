import logging

import sys
import os

# Add the parent directory to the Python path
# Use this line only if your want to test the script directly from the current path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Test get_views() method using the pageview API
import pywikibot
from suggestbot.utilities.page import Page

logging.basicConfig(level=logging.INFO)

site = pywikibot.Site("en")
site2 = pywikibot.Site("ar")
# page = Page(site, 'Barack Obama')
# print("{0} has a prediction of {1}".format(page.title(), page.get_prediction()))


page2 = Page(site2, "إيلون ماسك")
print("{0} has a prediction of {1}".format(page2.title(), page2.get_ar_prediction()))

page = Page(site, "Clarence Darrow")
print("{0} has a prediction of {1}".format(page.title(), page.get_prediction()))

page = Page(site, "Andre Dawson")
print("{0} has a prediction of {1}".format(page.title(), page.get_rating()))

page = Page(site, "2004 Chicago Bears season")
print("{0} has a prediction of {1}".format(page.title(), page.get_rating()))

page = Page(site, "Jack O'Callahan")
print("{0} has a prediction of {1}".format(page.title(), page.get_rating()))

page = Page(site, "Switchcraft")
print("{0} has a prediction of {1}".format(page.title(), page.get_prediction()))
