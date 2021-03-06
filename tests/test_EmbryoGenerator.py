import pytest

from mock import MagicMock, patch

from embryo.create import EmbryoGenerator


class TestEmbryoGenerator(object):

    @pytest.mark.parametrize('exists_embryo_object', [True, False])
    def test_embryo_pre_and_post_hooks_are_called(self, exists_embryo_object):
        name = 'name'
        dest = './'
        context = {'a': 1}
        loaded_context = dict(context)

        renderer = MagicMock()

        embryo = MagicMock()
        embryo.apply_pre_create.return_value = loaded_context

        generator = MagicMock()
        generator._build_renderer = lambda *args: EmbryoGenerator._build_renderer(generator, *args)
        generator._load_context = lambda *args: EmbryoGenerator._load_context(generator, *args)

        if exists_embryo_object:
            generator._load_embryo.return_value = embryo

            with patch('embryo.create.json'):
                with patch('embryo.create.Renderer') as Renderer:
                    Renderer.return_value = renderer
                    with patch('embryo.create.Yaml') as Yaml:
                        Yaml.read.return_value = {}
                        EmbryoGenerator.create(generator, name, dest, context)

            embryo.apply_pre_create.assert_called_once_with(context)
            embryo.apply_post_create.assert_called_once_with(renderer, loaded_context)
        else:
            generator._load_embryo.return_value = None

            with patch('embryo.create.json'):
                with patch('embryo.create.Renderer') as Renderer:
                    Renderer.return_value = renderer
                    with patch('embryo.create.Yaml') as Yaml:
                        Yaml.read.return_value = {}
                        EmbryoGenerator.create(generator, name, dest, context)

            embryo.apply_pre_create.assert_not_called()
            embryo.apply_post_create.assert_not_called()
