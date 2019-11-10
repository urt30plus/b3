from tests.plugins.censor import Detection_TestCase


class Test_Censor_badname(Detection_TestCase):
    """
    Test that bad names are detected.
    """

    def test_regexp(self):
        self.p._badNames = []
        self.assert_name_is_not_penalized('Joe')

        self.p._badNames = []
        self.p._add_bad_name(rulename='ass', regexp=r'\b[a@][s$]{2}\b')
        self.assert_name_is_penalized('ass')
        self.assert_name_is_penalized('a$s')
        self.assert_name_is_penalized(' a$s ')
        self.assert_name_is_penalized('kI$$ my a$s n00b')
        self.assert_name_is_penalized('right in the ass')

    def test_word(self):
        self.p._badNames = []
        self.assert_name_is_not_penalized('Joe')

        self.p._badNames = []
        self.p._add_bad_name(rulename='ass', word='ass')
        self.assert_name_is_penalized('ass')
        self.assert_name_is_penalized('dumb ass!')
        self.assert_name_is_penalized('what an ass')
