#!/usr/bin/env python
# -*- coding: utf-8  -*-
"""
XML-RPC wrapper to instantiate the co-edit recommendation server.

Copyright (C) 2005-2016 SuggestBot Dev Group

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

import sys
import os

# Add the parent directory to the Python path
# Use this line only if your want to test the script directly from the current path 
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import logging

from suggestbot import config
from suggestbot.recommenders.coedit import Recommender

from xmlrpc.server import SimpleXMLRPCServer
from xmlrpc.server import SimpleXMLRPCRequestHandler

# Restrict to a particular path
class RequestHandler(SimpleXMLRPCRequestHandler):
    rpc_paths = ('/RPC2',)

def main():
    # Parse CLI options
    import argparse
    cli_parser = argparse.ArgumentParser(
        description="XML-RPC server for co-edit based recommendations."
        )

    # Add verbosity option
    cli_parser.add_argument('-v', '--verbose', action='store_true',
                            help='Be more verbose')
    args = cli_parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.INFO)

    recserver = Recommender()
    server = SimpleXMLRPCServer(
        (config.coedit_hostname, config.coedit_hostport),
        allow_none=True)

    server.register_introspection_functions()
    server.register_function(recserver.recommend, 'recommend')
    print("Co-edit rec server is running...")

    # Run the server's main loop
    server.serve_forever()

if __name__ == "__main__":
    main()
