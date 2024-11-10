# Test get_views() method using the pageview API

import logging
logging.basicConfig(level=logging.INFO)

import sys
import os

# Add the parent directory to the Python path
# Use this line only if your want to test the script directly from the current path 
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pywikibot
import suggestbot.utilities.page as sup

site = pywikibot.Site('ar')

# pagelist = [sup.Page(site, 'Barack Obama'),
#             sup.Page(site, 'Ara Parseghian'),
#             sup.Page(site, 'Clarence Darrow'),
#             sup.Page(site, 'Andre Dawson'),
#             sup.Page(site, '2004 Chicago Bears season'),
#             sup.Page(site, "Jack O'Callahan"),
#             sup.Page(site, "Switchcraft")]

pagelist = [sup.Page(site, 'إلون ماسك'),
            sup.Page(site, 'المغرب'),
            sup.Page(site, 'فاس'),
            sup.Page(site, 'مرآة التيار'),
            ]
for page in sup.PredictionGenerator_QAF(pagelist):
    print("{0} has a page ID of {1}, last revision of {2}, and prediction of {3}".format(page.title(), page._pageid, page.latest_revision_id, page.get_prediction()))


#         site = pywikibot.Site('en', 'wikipedia')
#         pages = [pywikibot.Page(site, 'Example Page')]
#         
# for page in sup.get_batch_predictions(site, pagelist):
#    # print(f"Page: {page.title()}, Prediction: {page.prediction}")
#    print("{0} has a page ID of {1}, last revision of {2}, and prediction of {3}".format(page.title(), page._pageid, page.latestRevision(), page.get_prediction()))
    
