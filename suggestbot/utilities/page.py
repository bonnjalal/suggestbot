#!/usr/bin/env python
# -*- coding: utf-8  -*-
"""
Wikipedia page object with properties reflecting an article's
current assessment rating, it's predicted assessment rating,
and the average number of views over the past 14 days.  The
assessment rating is calculated by parsing talk page wikitext.
Predicted rating is calculated by the Lift Wing service. Page
views are grabbed from the Wikimedia Pageview API.

Copyright (C) 2005-2016 SuggestBot Dev Group
(Modifications 2025)

This library is free software; you can redistribute it and/or
modify it under the terms of the GNU Library General Public
License as published by the Free Software Foundation; either
version 2 of the License, or (at your option) any later version.

This library is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
Library General Public License for more details.

You should have received a copy of the GNU Library General Public
License along with this library; if not, write to the
Free Software Foundation, Inc., 51 Franklin St, Fifth Floor,
Boston, MA  02110-1301, USA.
"""

## Purpose of this module:
## Extend the Pywikibot page object with information on:
## 1: the page's assessment rating (by parsing wikitext)
## 2: predicted assessment rating by Lift Wing
## 3: page views for the past 14 days as well as average views/day
##     over the same time period
## 4: specific suggestions for article improvement

import logging
import json
from time import sleep
from datetime import date, timedelta
from urllib.parse import quote
from math import log

# from collections import namedtuple
# from mwtypes import Timestamp
import requests
import mwparserfromhell as mwp
import pywikibot
from pywikibot.pagegenerators import PreloadingGenerator
from pywikibot.tools.itertools import itergroup
from pywikibot.data import api
from pywikibot import backports

# from articlequality.extractors import enwiki  <- #DEPRECATED

from scipy import stats

from suggestbot import config
import suggestbot.utilities.qualmetrics as qm


class InvalidRating(Exception):
    """The given rating is not one we support."""

    pass


class Page(pywikibot.Page):
    def __init__(self, site, title, *args, **kwargs):
        super(Page, self).__init__(site, title, *args, **kwargs)

        self._avg_views = None  # avg views per last 14 days
        self._rating = None  # current assessment rating
        self._prediction = None  # predicted rating by Lift Wing

        self._wp10_scale = {r: i for i, r in enumerate(config.wp_ratings[site.lang])}
        self._qualdata = {}
        self._qualtasks = {}

        self._headers = {"User-Agent": config.http_user_agent, "From": config.http_from}

    def set_views(self, views):
        """
        Set the number of average views.

        :param views: Number of average views.
        :type views: float
        """
        self._avg_views = views

    def _get_views_from_api(self, http_session=None):
        """
        Make a request to the Wikipedia pageview API to retrieve page views
        for the past 14 days and calculate and set `_avg_views` accordingly.

        :param http_session: Session to use for HTTP requests
        :type http_session: requests.session
        """
        if not http_session:
            http_session = requests.Session()

        today = date.today()
        start_date = today - timedelta(days=15)
        end_date = today - timedelta(days=2)

        url = "{api_url}{lang}.wikipedia/all-access/all-agents/{title}/daily/{startdate}/{enddate}".format(
            api_url=config.pageview_url,
            lang=self.site.lang,
            title=quote(self.title(), safe=""),
            startdate=start_date.strftime("%Y%m%d"),
            enddate=end_date.strftime("%Y%m%d"),
        )

        view_list = []
        num_attempts = 0
        while not view_list and num_attempts < config.max_url_attempts:
            r = http_session.get(url, headers=self._headers)
            num_attempts += 1
            if r.status_code == 200:
                try:
                    response = r.json()
                    view_list = response["items"]
                except ValueError:
                    logging.warning("Unable to decode pageview API as JSON")
                    continue  # try again
                except KeyError:
                    logging.warning("Key 'items' not found in pageview API response")
            else:
                logging.warning("Pageview API did not return HTTP status 200")

        if view_list:
            total_views = 0
            days = 0
            for item in view_list:
                try:
                    total_views += item["views"]
                    days += 1
                except KeyError:
                    pass
            if days > 0:
                self._avg_views = total_views / days

        return ()

    def get_views(self, http_session=None):
        """
        Retrieve the average number of views for the past 14 days
        for this specific page.

        :param http_session: Session to use for HTTP requests
        :type http_session: requests.Session

        :returns: This page's number of average views
        """
        if self._avg_views is None:
            self._get_views_from_api(http_session=http_session)

        return self._avg_views

    def set_rating(self, new_rating):
        """
        Set this article's current assessment rating.

        :param new_rating: The new assessment rating
        """
        self._rating = new_rating

    def get_assessment(self, wikitext):
        """
        Parse the given wikitext and extract any assessment rating.

        This is a reimplementation of the logic from the deprecated
        'articlequality' library.

        If multiple ratings are present, the highest rating is used.

        :param wikitext: wikitext of a talk page
        :returns: assessment rating
        """

        rating = "na"
        ratings = []  # numeric ratings

        try:
            if len(wikitext) > 8 * 1024:
                wikitext = wikitext[: 8 * 1024]

            wikicode = mwp.parse(wikitext)
        except Exception as e:
            logging.warning(
                f"mwparserfromhell failed to parse wikitext for {self.title()}: {e}"
            )
            return "na"

        # Find all templates
        templates = wikicode.filter_templates()

        for t in templates:
            try:
                # Normalize template name to check if it's a WikiProject banner
                template_name = t.name.lower().strip().replace("_", " ")

                if not (
                    template_name.startswith("wikiproject")
                    or template_name.startswith("wp")
                    or "wiki project" in template_name
                ):
                    continue  # Not a wikiproject banner

                # Check if the template has a 'class' parameter
                if t.has("class"):
                    class_val = str(t.get("class").value).strip().lower()

                    if class_val in self._wp10_scale:
                        ratings.append(self._wp10_scale[class_val])

                    elif class_val in ("bplus", "b+"):
                        if "b" in self._wp10_scale:
                            ratings.append(self._wp10_scale["b"])
                    elif class_val in ("a-class", "aclass"):
                        if "a" in self._wp10_scale:
                            ratings.append(self._wp10_scale["a"])

            except Exception:
                continue

        if ratings:
            try:
                # set rating to the highest rating (max numeric value)
                best_rating_num = max(ratings)
                # Convert the number back to the string (e.g., 'b', 'ga')
                rating = {v: k for k, v in self._wp10_scale.items()}[best_rating_num]
            except Exception as e:
                logging.warning(f"Could not map rating number for {self.title()}: {e}")
                rating = "na"

        return rating

    def get_rating(self):
        """
        Retrieve the current article assessment rating as found on the
        article's talk page by parsing its wikitext.

        :returns: The article's assessment rating, 'na' if it is not assessed.
        """
        if self._rating is None:
            try:
                tp = self.toggleTalkPage()
                # Get the raw wikitext
                wikitext = tp.get()
                self._rating = self.get_assessment(wikitext)
            except pywikibot.exceptions.NoPageError:
                self._rating = "na"
            except pywikibot.exceptions.IsRedirectPageError:
                self._rating = "na"
            except Exception as e:
                logging.error(
                    f"Failed to get or parse talk page for {self.title()}: {e}"
                )
                self._rating = "na"

        return self._rating

    def set_prediction(self, prediction):
        """
        Set the article's predicted quality rating.

        :param prediction: Predicted quality rating.
        :type prediction: str
        """
        if not prediction in self._wp10_scale:
            raise InvalidRating

        self._prediction = prediction

    def _get_QAF_pred(self):
        """
        Make a request to Article Quality Feature api to get the predicted article rating.
        """
        langcode = "{lang}".format(lang=self.site.lang)

        url = "{qaf_api}lang={langcode}&title={title}".format(
            qaf_api=config.QAF_api, langcode=langcode, title=self.title()
        )

        rating = None
        num_attempts = 0
        while not rating and num_attempts < config.max_url_attempts:
            r = requests.get(url, headers=self._headers)
            num_attempts += 1
            if r.status_code == 200:
                try:
                    response = r.json()
                    rating = response["class"].lower()
                    break  # ok, done
                except ValueError:
                    logging.warning("Unable to decode QAF response as JSON")
                except KeyError:
                    logging.warning("QAF response keys not as expected")

            sleep(5)
        return rating

    def _get_liftwing_pred(self):
        """
        Make a request to Lift Wing to get the predicted article rating.
        """
        if not hasattr(self, "_revid"):
            try:
                self.site.loadrevisions(self)
            except Exception as e:
                logging.warning(f"Failed to load revision for {self.title()}: {e}")

        # Check again if loading failed or page has no revisions
        if not hasattr(self, "_revid"):
            logging.warning(f"No revid for page {self.title()}, skipping Lift Wing.")
            return None

        langcode = "{lang}wiki".format(lang=self.site.lang)

        model_name = f"{langcode}-articlequality"
        url = f"https://api.wikimedia.org/service/lw/inference/v1/models/{model_name}:predict"

        # Prepare headers and data for the POST request
        post_headers = self._headers.copy()
        post_headers["Content-Type"] = "application/json"

        data = {"rev_id": self._revid}

        rating = None
        num_attempts = 0
        while not rating and num_attempts < config.max_url_attempts:
            try:
                r = requests.post(url, headers=post_headers, data=json.dumps(data))
                num_attempts += 1

                if r.status_code == 200:
                    response = r.json()
                    rating = response[langcode]["scores"][str(self._revid)][
                        "articlequality"
                    ]["score"]["prediction"].lower()
                    break
                else:
                    logging.warning(
                        f"Lift Wing API returned status {r.status_code} for rev_id {self._revid}"
                    )

            except requests.exceptions.RequestException as e:
                logging.warning(f"Lift Wing request failed: {e}")
            except ValueError:
                logging.warning(
                    f"Unable to decode Lift Wing response as JSON for rev_id {self._revid}"
                )
            except KeyError:
                logging.warning(
                    f"Lift Wing response keys not as expected for rev_id {self._revid}"
                )

            sleep(1)
        return rating

    def get_prediction(self):
        """
        Retrieve the predicted assessment rating from Lift Wing using the
        current revision of the article.
        """
        if not self._prediction:
            self._prediction = self._get_liftwing_pred()

        return self._prediction

    def get_ar_prediction(self):
        """
        Retrieve the predicted assessment rating from QAF.
        """
        if not self._prediction:
            self._prediction = self._get_QAF_pred()

        return self._prediction

    def _get_qualmetrics(self):
        """
        Populate quality metrics used for task suggestions.
        """
        try:
            qualfeatures = qm.get_qualfeatures(self.get())
        except pywikibot.exceptions.NoPageError:
            return ()
        except pywikibot.exceptions.IsRedirectPageError:
            return ()

        # 1: length
        if qualfeatures.length > 0:
            self._qualdata["length"] = log(qualfeatures.length, 2)
        else:
            self._qualdata["length"] = 0
        # 2: lengthToRefs
        self._qualdata["lengthToRefs"] = qualfeatures.length / (
            1 + qualfeatures.num_references
        )
        # 3: completeness
        self._qualdata["completeness"] = 0.4 * qualfeatures.num_pagelinks
        # 4: numImages
        self._qualdata["numImages"] = qualfeatures.num_imagelinks
        # 5: headings
        self._qualdata["headings"] = (
            qualfeatures.num_headings_lvl2 + 0.5 * qualfeatures.num_headings_lvl3
        )

        return ()

    def get_suggestions(self):
        """
        Decide whether this article is in need of specific improvements,
        and if so, suggest those.
        """
        if not self._qualdata:
            self._get_qualmetrics()

        for key, keyDistr in config.task_dist.items():
            if not key in self._qualdata:
                logging.warning(
                    "Warning: suggestion key {0} not found in page data for {1}".format(
                        key, self.title()
                    )
                )
                continue

            if key == "lengthToRefs":
                pVal = 1 - keyDistr.cdf(self._qualdata[key])
            else:
                pVal = keyDistr.cdf(self._qualdata[key])

            logging.debug("pVal for {task} is {p:.5f}".format(task=key, p=pVal))
            verdict = "no"
            if pVal < config.task_p_yes:
                verdict = "yes"
            elif pVal < config.task_p_maybe:
                verdict = "maybe"
            self._qualtasks[key] = verdict

        return self._qualtasks


def TalkPageGenerator(pages):
    """
    Generate talk pages from a list of pages.
    """
    for page in pages:
        yield page.toggleTalkPage()


def RatingGenerator(pages, step=50):
    """
    Generate pages with assessment ratings.
    """

    # Preload talk page contents in bulk to speed up processing
    tp_map = {}
    for talkpage in PreloadingGenerator(TalkPageGenerator(pages), step=step):
        tp_map[talkpage.title(withNamespace=False)] = talkpage

    for page in pages:
        try:
            talkpage = tp_map[page.title()]
            page._rating = page.get_assessment(talkpage.get())
        except KeyError:
            page._rating = "na"
        except pywikibot.exceptions.NoPageError:
            page._rating = "na"
        except pywikibot.exceptions.IsRedirectPageError:
            page._rating = "na"
        yield page


def PageRevIdGenerator(site, pagelist, step=50):
    """
    Generate page objects with their most recent revision ID.
    """
    for sublist in backports.batched(pagelist, step):
        pageids = [
            str(p._pageid) for p in sublist if hasattr(p, "_pageid") and p._pageid > 0
        ]
        cache = dict((p.title(), p) for p in sublist)
        props = "revisions|info|categoryinfo"
        rvgen = api.PropertyGenerator(props, site=site)
        rvgen.set_maximum_items(-1)
        if len(pageids) == len(sublist):
            rvgen.request["pageids"] = "|".join(pageids)
        else:
            rvgen.request["titles"] = "|".join(list(cache.keys()))
        rvgen.request["rvprop"] = "ids|flags|timestamp|user|comment"

        logging.debug("Retrieving {n} pages from {s}.".format(n=len(cache), s=site))
        for pagedata in rvgen:
            logging.debug("Preloading {0}".format(pagedata))
            try:
                if pagedata["title"] not in cache:
                    for key in cache:
                        if site.sametitle(key, pagedata["title"]):
                            cache[pagedata["title"]] = cache[key]
                            break
                    else:
                        logging.warning(
                            "preloadpages: Query returned unexpected title"
                            "'%s'" % pagedata["title"]
                        )
                        continue
            except KeyError:
                logging.debug("No 'title' in %s" % pagedata)
                logging.debug("pageids=%s" % pageids)
                logging.debug("titles=%s" % list(cache.keys()))
                continue
            page = cache[pagedata["title"]]
            api.update_page(page, pagedata)

        for page in sublist:
            yield page


def PredictionGenerator(site, pages, step=50):
    """
    Generate pages with quality predictions using Lift Wing.
    """

    for page in PageRevIdGenerator(site, pages, step=step):
        try:
            page.get_prediction()
        except Exception as e:
            logging.warning(
                f"Failed to get Lift Wing prediction for {page.title()}: {e}"
            )

        yield page


def PredictionGenerator_QAF(pages, step=50):
    """
    Generate pages with quality predictions using quality article features api.
    """
    for page in pages:
        page.get_ar_prediction()
        yield page
