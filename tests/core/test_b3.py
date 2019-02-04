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

import os

import b3
import b3.parser
from tests import B3TestCase


class Test_getConfPath(B3TestCase):

    def test_get_b3_path(self):
        b3_path = b3.getB3Path()
        self.assertTrue(os.path.exists(b3_path))

    def test_getConfPath(self):
        self.console.config.fileName = "/some/where/conf/b3.xml"
        self.assertEqual('/some/where/conf', b3.getConfPath())
        self.console.config.fileName = "./b3.xml"
        self.assertEqual('.', b3.getConfPath())

    def test_getConfPath_invalid(self):
        self.assertRaises(TypeError, b3.getConfPath, {"decode": False, "conf": self})


class Test_loading_parser(B3TestCase):

    def test_load_parser(self):
        parser_class = b3.loadParser("iourt43")
        self.assertTrue(issubclass(parser_class, b3.parser.Parser))
