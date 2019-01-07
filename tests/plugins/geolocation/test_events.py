# -*- coding: utf-8 -*-

# ################################################################### #
#                                                                     #
#  BigBrotherBot(B3) (www.bigbrotherbot.net)                          #
#  Copyright (C) 2005 Michael "ThorN" Thornton                        #
#                                                                     #
#  This program is free software; you can redistribute it and/or      #
#  modify it under the terms of the GNU General Public License        #
#  as published by the Free Software Foundation; either version 2     #
#  of the License, or (at your option) any later version.             #
#                                                                     #
#  This program is distributed in the hope that it will be useful,    #
#  but WITHOUT ANY WARRANTY; without even the implied warranty of     #
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the       #
#  GNU General Public License for more details.                       #
#                                                                     #
#  You should have received a copy of the GNU General Public License  #
#  along with this program; if not, write to the Free Software        #
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA      #
#  02110-1301, USA.                                                   #
#                                                                     #
# ################################################################### #

import mock

from b3.plugins.geolocation.location import Location
from tests.plugins.geolocation import GeolocationTestCase
from tests import InstantThread

class Test_events(GeolocationTestCase):

    @mock.patch("threading.Thread", new_callable=lambda: InstantThread)
    def test_event_client_geolocation_success(self, instant_thread):
        # GIVEN
        self.mike.ip = '8.8.8.8'
        # WHEN
        self.mike.connects("1")
        # THEN
        self.assertEqual(True, hasattr(self.mike, 'location'))
        self.assertIsNotNone(self.mike.location)
        self.assertIsInstance(self.mike.location, Location)

    @mock.patch("threading.Thread", new_callable=lambda: InstantThread)
    def test_event_client_geolocation_failure(self, instant_thread):
        # GIVEN
        self.mike.ip = '--'
        # WHEN
        self.mike.connects("1")
        # THEN
        self.assertIsNone(self.mike.location)

    @mock.patch("threading.Thread", new_callable=lambda: InstantThread)
    def test_event_client_geolocation_success_maxmind(self, instant_thread):
        # GIVEN
        self.p._geolocators.pop(0)
        self.p._geolocators.pop(0)
        self.p._geolocators.pop(0)
        self.mike.ip = '8.8.8.8'
        # WHEN
        self.mike.connects("1")
        # THEN
        self.assertGreaterEqual(len(self.p._geolocators), 1)
        self.assertIsNotNone(self.mike.location)
        self.assertIsNone(self.mike.location.isp)

    @mock.patch("threading.Thread", new_callable=lambda: InstantThread)
    def test_event_client_geolocation_success_maxmind_using_event_client_update(self, instant_thread):
        # GIVEN
        self.p._geolocators.pop(0)
        self.p._geolocators.pop(0)
        self.p._geolocators.pop(0)
        self.mike.ip = ''
        self.mike.connects("1")
        # WHEN
        self.mike.ip = '8.8.8.8'
        self.mike.save(self.console)
        # THEN
        self.assertGreaterEqual(len(self.p._geolocators), 1)
        self.assertEqual(True, hasattr(self.mike, 'location'))
        self.assertIsNotNone(self.mike.location)
        self.assertIsInstance(self.mike.location, Location)
