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

        project = MagicMock()

        embryo = MagicMock()
        embryo.apply_pre_create.return_value = loaded_context

        generator = MagicMock()
        generator._build_project.return_value = project
        generator._load_context.return_value = context

        if exists_embryo_object:
            generator._load_embryo_object.return_value = embryo

            with patch('embryo.create.json'):
                EmbryoGenerator.create(generator, name, dest, context)

            embryo.apply_pre_create.assert_called_once_with(context)
            embryo.apply_post_create.assert_called_once_with(project, loaded_context)
        else:
            generator._load_embryo_object.return_value = None

            with patch('embryo.create.json'):
                EmbryoGenerator.create(generator, name, dest, context)

            embryo.apply_pre_create.assert_not_called()
            embryo.apply_post_create.assert_not_called()
