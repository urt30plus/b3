import unittest

from mock import Mock

from b3.parsers.q3a.abstractParser import AbstractParser


class Test(unittest.TestCase):

    def test_getCvar(self):
        # prepare mocks
        mock_parser = Mock(spec=AbstractParser)
        mock_parser._reCvarName = AbstractParser._reCvarName
        mock_parser._reCvar = AbstractParser._reCvar
        mock_parser.getCvar = AbstractParser.getCvar

        def assertGetCvar(cvar_name, gameserver_response, expected_response):
            mock_parser.write = Mock(return_value=gameserver_response)
            cvar = mock_parser.getCvar(mock_parser, cvar_name)
            if cvar is None:
                self.assertEqual(expected_response, None)
            else:
                self.assertEqual(expected_response, (cvar.name, cvar.value, cvar.default))

        assertGetCvar('g_password', '"g_password" is:"^7" default:"scrim^7"', ("g_password", '', "scrim"))
        assertGetCvar('g_password', '"g_password" is:"^7" default:"^7"', ("g_password", '', ""))
        assertGetCvar('g_password', '"g_password" is:"test^7" default:"^7"', ("g_password", 'test', ""))
        assertGetCvar('g_password', 'whatever', None)
        assertGetCvar('g_password', '"g_password" is:"^7"', ("g_password", '', None))
        assertGetCvar('sv_maxclients', '"sv_maxclients" is:"16^7" default:"8^7"', ("sv_maxclients", '16', '8'))
        assertGetCvar('g_maxGameClients', '"g_maxGameClients" is:"0^7", the default', ("g_maxGameClients", '0', '0'))
        assertGetCvar('mapname', '"mapname" is:"ut4_abbey^7"', ("mapname", 'ut4_abbey', None))


if __name__ == "__main__":
    unittest.main()
