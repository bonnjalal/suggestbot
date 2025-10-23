#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test the XML-RPC-based edit profiler.
"""

import sys
import os

# Add the parent directory to the Python path
# Use this line only if your want to test the script directly from the current path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import logging

from suggestbot import config
import xmlrpc.client


def main():
    # test_lang = "en"
    # test_user = "Nettrom"

    test_lang = "ar"
    test_user = "Bonnjalal00"

    sp = xmlrpc.client.ServerProxy(
        "http://{hostname}:{port}".format(
            hostname=config.edit_server_hostname, port=config.edit_server_hostport
        )
    )
    try:
        edits = sp.get_edits(test_user, test_lang, config.nedits)
        print("Got {} edits back".format(len(edits)))
    except xmlrpc.client.Error as e:
        logging.error(
            "Getting edits for {0}:User:{1} failed".format(test_lang, test_user)
        )
        logging.error(e)
    return ()


if __name__ == "__main__":
    main()
