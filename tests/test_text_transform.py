import pytest

from embryo.text_transform import TextTransform

TT = TextTransform

SNAKE_CASE = 'rock_and_roll_star'
CONST_CASE = 'DRIVE_ME_CRAZY'
DASH_CASE = 'when-do-we-get-paid'
CAMEL_CASE = 'SaveAPlant'
MIXED_CASE = '!@#$So-help-- --Me_god$$'
SPACE_STR = '  this   is   too  much   space    '


class TestTextTransform(object):
    @pytest.mark.parametrize(
        'value_was, value_is',
        [(MIXED_CASE, 'So help Me god'), (CAMEL_CASE, 'Save A Plant'),
         (CONST_CASE, 'DRIVE ME CRAZY'), (SNAKE_CASE, 'rock and roll star'),
         (DASH_CASE, 'when do we get paid'), (SPACE_STR,
                                              'this is too much space')])
    def test_normalize(self, value_was, value_is):
        assert TT.normalize(value_was) == value_is

    def test_split_class_name(self):
        assert TT.split_class_name(CAMEL_CASE) == 'Save A Plant'

    def test_non_word_to_space(self):
        assert TT.non_word_to_space(MIXED_CASE) == '    So help     Me god  '

    def test_reduce_spacing(self):
        assert TT.reduce_spacing(SPACE_STR) == 'this is too much space'

    @pytest.mark.parametrize(
        'value_was, value_is',
        [(MIXED_CASE, 'so_help_me_god'), (CAMEL_CASE, 'save_a_plant'),
         (CONST_CASE, 'drive_me_crazy'), (SNAKE_CASE, 'rock_and_roll_star'),
         (DASH_CASE, 'when_do_we_get_paid'), (SPACE_STR,
                                              'this_is_too_much_space')])
    def test_snake(self, value_was, value_is):
        assert TT.snake(value_was) == value_is

    @pytest.mark.parametrize(
        'value_was, value_is',
        [(MIXED_CASE, 'so-help-me-god'), (CAMEL_CASE, 'save-a-plant'),
         (CONST_CASE, 'drive-me-crazy'), (SNAKE_CASE, 'rock-and-roll-star'),
         (DASH_CASE, 'when-do-we-get-paid'), (SPACE_STR,
                                              'this-is-too-much-space')])
    def test_dash(self, value_was, value_is):
        assert TT.dash(value_was) == value_is

    def test_title(self):
        assert TT.title(SNAKE_CASE) == 'Rock And Roll Star'
