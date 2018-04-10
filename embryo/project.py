import os
from os.path import join

import yaml

from types import ModuleType

from jinja2 import Template
from yapf.yapflib.yapf_api import FormatCode
from appyratus.types import Yaml

from .constants import RE_RENDERING_METADATA, STYLE_CONFIG
from .environment import build_env
from .exceptions import TemplateNotFound


class Project(object):
    """
    A `Project` represents the schematics of a new, well, project of some sort
    in the host file system. It manages the creation of directories, files, and
    the rendering of templates into said files.
    """

    def __init__(
        self, root: str, tree: str, templates=None, dependencies=None
    ):
        """
        Initialize a project
        """

        self.root = root.rstrip('/')
        self.env = build_env()

        # if templates is a module extract its public string attributes
        # into the templates dict expected below.
        self.templates = {}

        # dependencies allow for specific ordering of templates in an embryo
        self.dependencies = dependencies

        if isinstance(templates, ModuleType):
            tmp_templates = {}
            for k in dir(templates):
                v = getattr(templates, k)
                if (not k.startswith('_')) and isinstance(v, (str, Template)):
                    tmp_templates[k] = v
            templates = tmp_templates

        # initialize jinja2 templates
        for k, v in (templates or {}).items():
            if isinstance(v, Template):
                self.templates[k] = v
            else:
                self.templates[k] = self.env.from_string(v)

        self.file_paths = set()
        self.directory_paths = set()
        self.render_metadata = {}

        # finally, initializes the instance attributes declared above.
        self.tree = self._init_tree(yaml.load(tree))

    def _init_tree(self, tree, parent_path: str = '') -> dict:
        """
        Initializes `directory_paths`, `file_paths`, and `render_metadata`. It
        returns a dict-based tree structure.
        """
        result = {}
        if not tree:
            return result
        for obj in tree:
            if isinstance(obj, dict):
                k = list(obj.keys())[0]
                v = obj[k]
                if isinstance(v, str):
                    # in this case, we have a file name with associated
                    # template rendering metadata we must parse out.
                    file_name = k
                    match = RE_RENDERING_METADATA.match(v)
                    tpl_name, ctx_key = match.groups()
                    file_path = join(parent_path, file_name)
                    self.render_metadata[file_path] = {
                        'template_name': tpl_name,
                        'context_path': ctx_key,
                    }
                    self.file_paths.add(file_path)
                    result[k] = True
                else:
                    # call _init_tree on subdirectory
                    path = join(parent_path, k)
                    result[k] = self._init_tree(obj[k], path)
                    self.directory_paths.add(path)
            elif obj.endswith('/'):
                # it'sn empty directory name
                dir_name = obj

                self.directory_paths.add(join(parent_path, dir_name))
                result[dir_name] = False
            else:
                # it's a plain ol' file name
                file_name = obj
                file_path = join(parent_path, file_name)
                self.file_paths.add(file_path)
                if file_path in self.templates:
                    # attempt to resolve the full path
                    self.render_metadata[file_path] = {
                        'template_name': file_path,
                        'context_path': None,
                    }
                elif file_name in self.templates:
                    # top-level resolution of file name only
                    self.render_metadata[file_path] = {
                        'template_name': file_name,
                        'context_path': None,
                    }
                result[file_name] = True
        return result

    def build(self, context: dict, style_config: dict = None) -> None:
        """
        Args:
            - context: a context dict for use by jinja2 templates.
            - style_config: yapf style options for code formating>

        1. Create the directories and files in the file system.
        2. Render templates into said files.
        """
        self.touch()    # create the project file structure

        for file_path in self.file_paths:
            meta = self.render_metadata.get(file_path)

            if meta is not None:
                tpl_name = meta['template_name']
                ctx_path = meta.get('context_path')
                ctx_obj = context

                # result the context sub-object to pass into
                # the template as its context
                if ctx_path:
                    for k in ctx_path.split('.'):
                        ctx_obj = ctx_obj[k]

                # render the template to file_path
                print(file_path)
                self.render(
                    file_path, tpl_name, ctx_obj, style_config=style_config
                )

    def touch(self) -> None:
        """
        Creates files and directories in the file system. This will not
        overwrite anything.
        """
        if not os.path.exists(self.root):
            os.makedirs(self.root)
        for dir_path in self.directory_paths:
            path = join(self.root, './{}'.format(dir_path))
            if not os.path.exists(path):
                os.makedirs(path)
        for file_path in self.file_paths:
            path = join(self.root, './{}'.format(file_path))
            open(path, 'a').close()

    def render(
        self,
        file_path: str,
        template_name: str,
        context: dict,
        style_config: dict = None
    ) -> None:
        """
        Renders a template to a file, provided that the `file_path` provided is
        recognized by this `Project`.
        """
        try:
            template = self.templates[template_name]
        except KeyError as exc:
            raise TemplateNotFound(template_name)

        style_config = style_config or STYLE_CONFIG
        rendered_text = template.render(context).strip()

        if file_path.endswith('.py'):
            formatted_text = FormatCode(
                rendered_text, style_config=style_config
            )[0]
        else:
            formatted_text = rendered_text

        self.write(file_path, formatted_text)

    def write(self, file_path: str, text: str) -> None:
        """
        Writes a string to a file, provided that the `file_path` provided is
        recognized by this `Project`.
        """
        assert file_path in self.file_paths
        file_path = file_path.strip('/')
        path = join(self.root, file_path)
        with open(path, 'w') as f_out:
            f_out.write(text)

    def has_directory(self, path) -> bool:
        """
        Return True if the given path is a directory path. The path must be
        recognized by this `Project`.
        """
        key = '/' + path.strip('/')
        return self.directory_paths.get(key)

    def has_file(self, path) -> bool:
        """
        Return True if the given path is a file path. The path must be
        recognized by this `Project`.
        """
        key = '/' + path.strip('/')
        return self.file_paths.get(key)
