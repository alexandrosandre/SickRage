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

from __future__ import print_function, unicode_literals

import unittest

import sickrage
from sickrage.core.common import ANY, Quality, WANTED
from sickrage.core.tv.episode import TVEpisode
from sickrage.core.tv.show import TVShow
from sickrage.providers import sortedProviderDict, GenericProvider
from tests import SiCKRAGETestDBCase


tests = {"Game of Thrones":
             {"tvdbid": 121361, "s": 5, "e": [10],
              "s_strings": [{"Season": ["Game of Thrones S05"]}],
              "e_strings": [{"Episode": ["Game of Thrones S05E10"]}]}}


class SearchTest(SiCKRAGETestDBCase):
    def __init__(self, something):
        super(SearchTest, self).__init__(something)


def test_generator(curData, name, provider, forceSearch):
    def test(self):
        show = TVShow(1, int(curData[b"tvdbid"]))
        show.name = name
        show.quality = ANY | Quality.UNKNOWN | Quality.RAWHDTV
        show.saveToDB()
        sickrage.showList.append(show)

        for epNumber in curData[b"e"]:
            episode = TVEpisode(show, curData[b"s"], epNumber)
            episode.status = WANTED

            # We arent updating scene numbers, so fake it here
            episode.scene_season = curData[b"s"]
            episode.scene_episode = epNumber

            episode.saveToDB()

            provider.show = show
            season_strings = provider._get_season_search_strings(episode)
            episode_strings = provider._get_episode_search_strings(episode)

            fail = False
            for cur_string in season_strings, episode_strings:
                if not all([isinstance(cur_string, list), isinstance(cur_string[0], dict)]):
                    print(" %s is using a wrong string format!" % provider.name)
                    print(cur_string)
                    fail = True
                    continue

            if fail:
                continue

            try:
                assert (season_strings == curData[b"s_strings"])
                assert (episode_strings == curData[b"e_strings"])
            except AssertionError:
                continue

            search_strings = episode_strings[0]
            # search_strings.update(season_strings[0])
            # search_strings.update({"RSS":['']})

            # print search_strings

            if not provider.public:
                continue

            items = provider._doSearch(search_strings)
            if not items:
                print("No results from provider?")
                continue

            title, url = provider._get_title_and_url(items[0])
            for word in show.name.split(" "):
                if not word.lower() in title.lower():
                    print("Show name not in title: %s. URL: %s" % (title, url))
                    continue

            if not url:
                print("url is empty")
                continue

            quality = provider.getQuality(items[0])
            size = provider._get_size(items[0])
            if not show.quality & quality:
                print("Quality not in ANY, %r" % quality)
                continue

    return test

# create the test methods
for forceSearch in (True, False):
    for name, curData in tests.items():
        fname = name.replace(' ', '_')

        for provider in sortedProviderDict().values():
            if provider.type == GenericProvider.TORRENT:
                if forceSearch:
                    test_name = 'test_manual_%s_%s_%s' % (fname, curData[b"tvdbid"], provider.name)
                else:
                    test_name = 'test_%s_%s_%s' % (fname, curData[b"tvdbid"], provider.name)
                test = test_generator(curData, name, provider, forceSearch)
                setattr(SearchTest, test_name, test)


if __name__ == '__main__':
    print("==================")
    print("STARTING - SEARCH TESTS")
    print("==================")
    print("######################################################################")
    unittest.main()
