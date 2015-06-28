#!/usr/env/python
# -*- coding: utf-8 -*-
'''
Library for handling suggestion requests for WikiProjects
using the WikiProject X page and task template layout.

Copyright (C) 2015 SuggestBot Dev Group

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
'''

import re

import logging
import requests

from datetime import datetime, timezone

import pywikibot
import mwparserfromhell as mwp

from reqhandler import RequestTemplateHandler

from suggestbot import config

class WikiProjectRequest:
    def __init__(self, projname, projpage,
                 projcat=None):
        '''
        :param projname: Name of the WikiProject we're suggesting to
        :type projname: str

        :param projpage: Page we're posting suggestions to
        :type projpage: str
        '''
        self.name = projname
        self.page = projpage
        self.category = projcat

        # Is it time to post again? Default is yes
        self.update = True

class WikiProjectHandler(RequestTemplateHandler):
    def __init__(self, lang=u'en',
                 name_pattern=ur'^WikiProject'):
        """
        Initialise an object that will handle WikiProject requests
        added to WikiProject pages.

        :param lang: What language Wikipedia we are working on
        :type lang: unicode

        :param name_pattern: Regular expression pattern to match names of pages,
                             if a page does not match this pattern it is not processed.
        :type name_pattern: unicode
        """
        
        super(self.__class__, self).__init__(lang=lang,
                                             templates={},
                                             ignoreList=config.wikiproj_ignores)
        self.name_pattern = re.compile(name_pattern, re.I)
        self.wikiproj_template = config.wikiproj_template.lower()

        # Regular expression for splitting a project page into project name
        # and sub page parts.
        self.subpage_re = re.compile(ur'(?P<projname>[^/]+)(?P<subname>/.*)')

    def processs_requests(self):
        '''
        Find and process all WikiProject requests for suggestions.  Requests
        are discovered through transclusions of the SuggestBot template for
        WikiProject requests (`suggestbot.config.wikiproj_template`), and
        by polling the WikiProject X config URL
        (`suggestbot.config.wikiproj_config_url`).
        '''

        wproj_reqs = {} # maps project name to project request object

        # Find transclusions of the WikiProject template
        template_page = pywikibot.Page(self.site, config.wikiproj_template)
        for tr_page in template_page.embeddedin(filter_redirects=False,
                                                namespaces=[4],
                                                content=True):
            if tr_page.title() in self.ignoreList:
                continue

            if not tr_page.canBeEdited():
                logging.warning('SuggestBot cannot edit {0} (page locked?), skipping'.format(tr_page.title()))
                continue

            logging.info('now processing request on {0}'.format(tr_page.title()))

            parsed_text = mwp.parse(tr_page.get())
            for template in parsed_text.filter_templates(recursive=True):
                template_name = template.name().strip().lower()
                if template_name == self.wikiproj_template:
                    # page title (without namespace) must match project name pattern
                    if not self.name_pattern.match(tr_page.title(withNamespace=False)):
                        continue
                    
                    # strip off subpage to get project name
                    match_obj = self.subpage_re.match(
                        tr_page.title(withNamespace=False))
                    if not match_obj:
                        # this is not supposed to happen
                        logging.warning('Template found, but not a project sub-page, ignoring this page')
                        continue
                    
                    project_name = match_obj.group('projname')
                    ## Store this request
                    wproj_reqs[project_name] = WikiProjectRequest(
                        project_name, tr_page)

        # Poll the WikiProject X config url
        req = requests.get(config.wikiproj_config_url)
        wpx_config = req.json()
        for project in wpx_config['projects']:
            if project['suggestbot']:
                project_page = pywikibot.Page(project['name'])
                project_name = project.page.title(withNamespace=False)
                project_post_page = pywikibot.Page('{0}{1}'.format(
                    project_page, config.wikiproject_subpage))

                ## Store this request, with category from 'source' parameter
                wproj_reqs[project_name] = WikiProjectRequest(
                    project_name, project_post_page,
                    project['source'])


        # Go through all requests and cancel the update flag for all
        # projects we've posted to in the last `config.wikiproject_delay` days.
        today = datetime.now(timezone.utc).date()
        for project in wproj_reqs.items():
            for (revid, revtime, revuse, revcomment) \
                in project.page.getVersionHistory(total=50):
                # NOTE: we assume we're found in < 50 revisions
                if username == self.site.user() \
                   and (today - revtime.date()).days < config.wikiproject_delay:
                    project.update = False

        # Go through all requests that are to be processed, fetch articles
        # from project categories

        # Get suggestions

        # Post suggestions
        


def main():
    """
    Run some tests.
    """

    from suggestbot import SuggestBot

    myBot = SuggestBot()
    myHandler = WikiProjectHandler(templates=templates);
    logging.info(u"instantiated WikiProjectHandler and SuggestBot objects, testing request handling...");

    try:
        recRequests = myHandler.getRequests();
        for (page, pageData) in recRequests.iteritems():
            logging.info(u"Found the following templates on page {page}:".format(page=page.title()).encode('utf-8'))

            for template in pageData['templates']:
                logging.info(u"- {template}".format(template=template.title()).encode('utf-8'))

            logging.info("\nIn the templates were listed the following articles:")

            for intPage in pageData['articles']:
                logging.info(u"- {page}".format(page=intPage.title()).encode('utf-8'))
            logging.info("")

        # Uncomment when doing live testing...
        if not myHandler.db.connect():
            logging.error("unable to connect to database");
        else:
            for (page, pageData) in recRequests.iteritems():
                myHandler.processSingleRequest(userPage=page,
                                               interestPages=pageData['articles'],
                                               knownTemplates=pageData['templates'],
                                               bot=myBot);
            myHandler.db.disconnect();
    finally:
        myHandler.stopme();

    # OK, done...
    return;

if __name__ == "__main__":
    main();
