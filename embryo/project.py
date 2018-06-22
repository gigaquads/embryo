import os

import json
import yaml

from typing import Dict
from types import ModuleType
from os.path import join
from copy import deepcopy

from jinja2 import Template
from yapf.yapflib.yapf_api import FormatCode
from appyratus.types import Yaml

from .constants import RE_RENDERING_METADATA, STYLE_CONFIG
from .environment import build_env
from .exceptions import TemplateNotFound
from .utils import say


class Project(object):
    """
    A `Project` represents the schematics of a new, well, project of some sort
    in the host file system. It manages the creation of directories, files, and
    the rendering of templates into said files.
    """

    def __init__(self, root: str, tree: str, templates=None):
        """
        Initialize a project
        """
        self.root = root.rstrip('/')
        self.fpaths = set()
        self.directory_paths = set()
        self.template_meta = {}
        self.nested_embryos = []
        self.fs = {}
        self.templates = self._init_templates(templates)
        self.tree = self._init_tree(tree)

    def _init_templates(self, templates):
        """
        Load template files from a templates module, ignoring any "private"
        object starting with an _. Return a dict, mapping each Template
        object's name to the object.
        """
        # if templates is a module extract its public string attributes
        # into the templates dict expected below.
        if isinstance(templates, ModuleType):
            tmp_templates = {}
            for k in dir(templates):
                v = getattr(templates, k)
                if (not k.startswith('_')) and isinstance(v, (str, Template)):
                    tmp_templates[k] = v
            templates = tmp_templates

        # load the jinja2 templates contained in the module, either in the form
        # of Template objects or strings.
        loaded_templates = {}
        jinja_env = build_env()

        if templates:
            for k, v in templates.items():
                if isinstance(v, Template):
                    loaded_templates[k] = v
                elif isinstance(v, str):
                    loaded_templates[k] = jinja_env.from_string(v)

        return loaded_templates

    def _init_tree(self, tree, parent_path: str = '') -> dict:
        """
        Initializes `directory_paths`, `fpaths`, and `template_meta`. It
        returns a dict-based tree structure.
        """
        if isinstance(tree, str):
            tree = yaml.load(tree)

        result = {}

        if not tree:
            return result

        def set_fs(path):
            fpath = os.path.join(path, '.embryo/context.json')
            context = {}
            if os.path.isfile(fpath):
                with open(fpath) as fin:
                    json_str = fin.read()
                    if json_str:
                        context = json.loads(json_str)

            if context is None:
                return

            abspath = os.path.abspath(path)
            self.fs['/' + path] = {
                'context': context,
                'path': abspath,
            }

        for obj in tree:
            if isinstance(obj, dict):
                k = list(obj.keys())[0]
                v = obj[k]
                if isinstance(v, str):
                    # in this case, we have a file name or nested embryo with
                    # associated template rendering metadata we must parse out.
                    match = RE_RENDERING_METADATA.match(v)
                    if k == 'embryo':
                        # embryo:falcon_app(foo)
                        nested_embryo_name, ctx_key = match.groups()
                        self.nested_embryos.append({
                            'embryo_name': nested_embryo_name,
                            'context_path': ctx_key,
                            'dir_path': parent_path,
                        })
                    else:
                        fname = k
                        tpl_name, ctx_key = match.groups()
                        fpath = join(parent_path, fname)
                        self.template_meta[fpath] = {
                            'template_name': tpl_name,
                            'context_path': ctx_key,
                        }
                        self.fpaths.add(fpath)
                        result[k] = True
                else:
                    # call _init_tree on subdirectory
                    child_path = join(parent_path, k)
                    result[k] = self._init_tree(obj[k], child_path)
                    self.directory_paths.add(child_path)
                    set_fs(parent_path)
            elif obj.endswith('/'):
                # it's an empty directory name
                dir_name = obj
                self.directory_paths.add(join(parent_path, dir_name))
                result[dir_name] = False
            else:
                # it's a plain ol' file name
                fname = obj
                fpath = join(parent_path, fname)
                self.fpaths.add(fpath)
                if fpath in self.templates:
                    # attempt to resolve the full path
                    self.template_meta[fpath] = {
                        'template_name': fpath,
                        'context_path': None,
                    }
                elif fname in self.templates:
                    # top-level resolution of file name only
                    self.template_meta[fpath] = {
                        'template_name': fname,
                        'context_path': None,
                    }
                result[fname] = True

        return result

    def build(
        self,
        embryo: 'Embryo',
        context: Dict,
        style_config: Dict = None
    ) -> None:
        """
        # Args
        - embryo: the Embryo object
        - context: a context dict for use by jinja2 templates.
        - style_config: yapf style options for code formating>

        1. Create the directories and files in the file system.
        2. Render templates into said files.
        """
        self.touch()    # create the project file structure

        say('Running Embryo.on_create hook...')
        embryo.apply_on_create(self, context, self.fs)

        context.setdefault('context', deepcopy(context))
        context.setdefault('fs', self.fs)

        for fpath in self.fpaths:
            meta = self.template_meta.get(fpath)

            if meta is not None:
                tpl_name = meta['template_name']
                ctx_path = meta.get('context_path')
                ctx_obj = context

                # result the context sub-object to pass into
                # the template as its context
                if ctx_path:
                    for k in ctx_path.split('.'):
                        ctx_obj = ctx_obj[k]

                assert fpath in self.fpaths

                # render the template to fpath
                abs_fpath = os.path.join(self.root, fpath.lstrip('/'))
                self.render(
                    abs_fpath, tpl_name, ctx_obj, style_config=style_config
                )

        del context['context']

        return self.nested_embryos

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
        for fpath in self.fpaths:
            path = join(self.root, './{}'.format(fpath))
            open(path, 'a').close()

    def render(
        self,
        abs_fpath: str,
        template_name: str,
        context: dict,
        style_config: dict = None
    ) -> None:
        """
        Renders a template to a file, provided that the `abs_fpath` provided is
        recognized by this `Project`.
        """
        try:
            template = self.templates[template_name]
        except KeyError:
            raise TemplateNotFound(template_name)

        try:
            print('>>> Rendering {}'.format(abs_fpath))
            rendered_text = template.render(context).strip()
        except:
            # TODO: create and use log util function
            print('>>> Problem rendering {}'.format(abs_fpath))
            raise

        if abs_fpath.endswith('.py'):
            style_config = style_config or STYLE_CONFIG
            try:
                formatted_text = FormatCode(
                    rendered_text, style_config=style_config
                )[0]
            except:
                # TODO: create and use log util function
                print('>>> Problem formatting {}'.format(abs_fpath))
                raise
        else:
            formatted_text = rendered_text

        self.write(abs_fpath, formatted_text)

    def write(self, fpath: str, text: str) -> None:
        """
        Writes a string to a file, provided that the `fpath` provided is
        recognized by this `Project`.
        """
        abs_fpath = join(self.root, fpath.strip())
        with open(abs_fpath, 'w') as f_out:
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
        return self.fpaths.get(key)
