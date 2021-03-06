#!/usr/bin/env python2

# Author: echel0n <sickrage.tv@gmail.com>
# URL: http://www.github.com/sickragetv/sickrage/
#
# This file is part of SickRage.
#
# SickRage is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# SickRage is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with SickRage.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals

import time
import traceback

from requests.auth import AuthBase

import sickrage
from sickrage.core.caches import tv_cache
from sickrage.providers import TorrentProvider


class T411Provider(TorrentProvider):
    def __init__(self):
        super(T411Provider, self).__init__("T411")

        self.supportsBacklog = True

        self.username = None
        self.password = None
        self.ratio = None
        self.token = None
        self.tokenLastUpdate = None

        self.cache = T411Cache(self)

        self.urls = {'base_url': 'http://www.t411.in/',
                     'search': 'https://api.t411.in/torrents/search/%s?cid=%s&limit=100',
                     'rss': 'https://api.t411.in/torrents/top/today',
                     'login_page': 'https://api.t411.in/auth',
                     'download': 'https://api.t411.in/torrents/download/%s'}

        self.url = self.urls['base_url']

        self.subcategories = [433, 637, 455, 639]

        self.minseed = 0
        self.minleech = 0
        self.confirmed = False

    def _doLogin(self):

        if self.token is not None:
            if time.time() < (self.tokenLastUpdate + 30 * 60):
                return True

        login_params = {'username': self.username,
                        'password': self.password}

        response = self.getURL(self.urls['login_page'], post_data=login_params, timeout=30, json=True)
        if not response:
            sickrage.LOGGER.warning("Unable to connect to provider")
            return False

        if response and 'token' in response:
            self.token = response[b'token']
            self.tokenLastUpdate = time.time()
            self.uid = response[b'uid'].encode('ascii', 'ignore')
            self.session.auth = T411Auth(self.token)
            return True
        else:
            sickrage.LOGGER.warning("Token not found in authentication response")
            return False

    def _doSearch(self, search_params, search_mode='eponly', epcount=0, age=0, epObj=None):

        results = []
        items = {'Season': [], 'Episode': [], 'RSS': []}

        if not self._doLogin():
            return results

        for mode in search_params.keys():
            sickrage.LOGGER.debug("Search Mode: %s" % mode)
            for search_string in search_params[mode]:

                if mode is not 'RSS':
                    sickrage.LOGGER.debug("Search string: %s " % search_string)

                searchURLS = \
                    ([self.urls['search'] % (search_string, u) for u in self.subcategories], [self.urls['rss']])[
                        mode is 'RSS']
                for searchURL in searchURLS:
                    sickrage.LOGGER.debug("Search URL: %s" % searchURL)
                    data = self.getURL(searchURL, json=True)
                    if not data:
                        continue

                    try:
                        if 'torrents' not in data and mode is not 'RSS':
                            sickrage.LOGGER.debug("Data returned from provider does not contain any torrents")
                            continue

                        torrents = data[b'torrents'] if mode is not 'RSS' else data

                        if not torrents:
                            sickrage.LOGGER.debug("Data returned from provider does not contain any torrents")
                            continue

                        for torrent in torrents:
                            if mode is 'RSS' and int(torrent[b'category']) not in self.subcategories:
                                continue

                            try:
                                title = torrent[b'name']
                                torrent_id = torrent[b'id']
                                download_url = (self.urls['download'] % torrent_id).encode('utf8')
                                if not all([title, download_url]):
                                    continue

                                size = int(torrent[b'size'])
                                seeders = int(torrent[b'seeders'])
                                leechers = int(torrent[b'leechers'])
                                verified = bool(torrent[b'isVerified'])

                                # Filter unseeded torrent
                                if seeders < self.minseed or leechers < self.minleech:
                                    if mode is not 'RSS':
                                        sickrage.LOGGER.debug(
                                                "Discarding torrent because it doesn't meet the minimum seeders or leechers: {0} (S:{1} L:{2})".format(
                                                        title, seeders, leechers))
                                    continue

                                if self.confirmed and not verified and mode is not 'RSS':
                                    sickrage.LOGGER.debug(
                                            "Found result " + title + " but that doesn't seem like a verified result so I'm ignoring it")
                                    continue

                                item = title, download_url, size, seeders, leechers
                                if mode is not 'RSS':
                                    sickrage.LOGGER.debug("Found result: %s " % title)

                                items[mode].append(item)

                            except Exception:
                                sickrage.LOGGER.debug("Invalid torrent data, skipping result: %s" % torrent)
                                sickrage.LOGGER.debug("Failed parsing provider. Traceback: %s" % traceback.format_exc())
                                continue

                    except Exception:
                        sickrage.LOGGER.error("Failed parsing provider. Traceback: %s" % traceback.format_exc())

            # For each search mode sort all the items by seeders if available if available
            items[mode].sort(key=lambda tup: tup[3], reverse=True)

            results += items[mode]

        return results

    def seedRatio(self):
        return self.ratio


class T411Auth(AuthBase):
    """Attaches HTTP Authentication to the given Request object."""

    def __init__(self, token):
        self.token = token

    def __call__(self, r):
        r.headers[b'Authorization'] = self.token
        return r


class T411Cache(tv_cache.TVCache):
    def __init__(self, provider_obj):
        tv_cache.TVCache.__init__(self, provider_obj)

        # Only poll T411 every 10 minutes max
        self.minTime = 10

    def _getRSSData(self):
        search_params = {'RSS': ['']}
        return {'entries': self.provider._doSearch(search_params)}
