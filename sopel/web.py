# coding=utf-8
"""
*Availability: 7+, deprecated in 6.2.0*

The web class contains essential web-related functions for interaction with web
applications or websites in your modules.  It supports HTTP GET, HTTP POST and
HTTP HEAD.
"""
# Copyright © 2008, Sean B. Palmer, inamidst.com
# Copyright © 2009, Michael Yanovich <yanovich.1@osu.edu>
# Copyright © 2012, Dimitri Molenaars, Tyrope.nl.
# Copyright © 2012-2013, Elad Alfassa, <elad@fedoraproject.org>
# Copyright © 2019, dgw, technobabbl.es
# Licensed under the Eiffel Forum License 2.

from __future__ import unicode_literals, absolute_import, print_function, division

# Imports to facilitate transition from sopel.web to sopel.tools.web
from sopel.tools.web import (  # noqa
    MockHttpResponse,
    USER_AGENT,
    default_headers,
    ca_certs,
    get,
    post,
    head,
    entity,
    decode,
    get_urllib_object,
    quote,
    quote_query,
    urlencode_non_ascii,
    iri_to_uri,
    urlencode,
)
