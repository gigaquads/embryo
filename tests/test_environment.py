import pytest

from embryo.environment import build_env, jinja2


class TestEnvironment(object):
    def test_build_env_provides_env(self):
        env = build_env()
        assert isinstance(env, jinja2.Environment)

    def test_env_has_custom_filters(self):
        env = build_env()
        for custom_filter in ('snake', 'dash', 'title'):
            assert custom_filter in env.filters

    def test_replacing_title_filter_will_take_effect(self):
        env = build_env()
        title = env.from_string('{{ val|title }}').render(
            dict(val='ABadTitle'))
        assert title == 'A Bad Title'
