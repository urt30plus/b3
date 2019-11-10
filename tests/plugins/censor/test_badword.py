from tests.plugins.censor import Detection_TestCase


class Test_Censor_badword(Detection_TestCase):
    """
    Test that bad words are detected.
    """

    def test_word(self):
        self.p._badNames = []
        self.assert_chat_is_not_penalized('Joe')

        self.p._badNames = []
        self.p._add_bad_word(rulename='ass', word='ass')
        self.assert_chat_is_penalized('ass')
        self.assert_chat_is_penalized('dumb ass!')
        self.assert_chat_is_penalized('what an ass')
        self.assert_chat_is_not_penalized('nice one!')

    def test_regexp(self):
        self.p._badWords = []
        self.assert_chat_is_not_penalized('Joe')

        self.p._badWords = []
        self.p._add_bad_word(rulename='ass', regexp=r'\b[a@][s$]{2}\b')
        self.assert_chat_is_penalized('what an ass!')
        self.assert_chat_is_penalized('a$s')
        self.assert_chat_is_penalized('in your a$s! noob')
        self.assert_chat_is_penalized('kI$$ my a$s n00b')
        self.assert_chat_is_penalized('right in the ass')

        self.p._badWords = []
        self.p._add_bad_word(rulename='ass', regexp=r'f[u\*]+ck')
        self.assert_chat_is_penalized('fuck')
        self.assert_chat_is_penalized(' fuck ')
        self.assert_chat_is_penalized(' fuck !')
        self.assert_chat_is_penalized('fuck!')
        self.assert_chat_is_penalized('fuck#*!')
        self.assert_chat_is_penalized('you fat fuck')
        self.assert_chat_is_penalized('f*ck u')
        self.assert_chat_is_penalized('f*****ck')
        self.assert_chat_is_penalized('f*uu**ck')
