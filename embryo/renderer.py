import os

import json
import yaml

from collections import defaultdict
from typing import Dict, List
from types import ModuleType
from os.path import join
from copy import deepcopy

from jinja2 import Template
from yapf.yapflib.yapf_api import FormatCode
from appyratus.types import Yaml
from appyratus.json import JsonEncoder

from .constants import RE_RENDERING_METADATA, STYLE_CONFIG
from .environment import build_env
from .exceptions import TemplateNotFound
from .utils import say, shout


class Renderer(object):
    """
    A `Renderer`  is responsible for taking the loaded instructions owned by an
    `Embryo` object and generating files into the filesystem.
    """

    _json_encoder = JsonEncoder()

    def __init__(self, embryo: 'Embryo'):
        """
        Initialize a renderer
        """
        self._embryo = embryo
        self.root = embryo.destination.rstrip('/')
        self.fpaths = set()
        self.directory_paths = set()
        self.template_meta = {}
        self.nested_embryos = []

        # these are initialized in the build method:
        self.tree = None
        self._jinja2_templates = None

    def render(self, style_config: Dict = None) -> None:
        """
        # Args
        - embryo: the Embryo object
        - context: a context dict for use by jinja2 templates.
        - style_config: yapf style options for code formating>

        1. Create the directories and files in the file system.
        2. Render templates into said files.
        """
        self._build_jinja2_templates()
        self._analyze_embryo()

        say('Context:\n\n{ctx}\n', ctx=json.dumps(
            json.loads(self._json_encoder.encode(self._embryo.context)),
            indent=2,
            sort_keys=True
        ))

        say('Tree:\n\n{tree}', tree='\n'.join(
            ' ' * 4 + line for line in yaml.dump(
                self._embryo.tree,
                default_flow_style=False,
                indent=2,
            ).split('\n')
        ))

        self._touch_filesystem()
        self._render_files(style_config)
        self._embryo.persist()

    def _build_jinja2_templates(self):
        """
        Load template files from a templates module, ignoring any "private"
        object starting with an _. Return a dict, mapping each Template
        object's name to the object.
        """
        templates = self._embryo.templates

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

        self._jinja2_templates = loaded_templates

    def _analyze_embryo(self):
        self._analyze_tree(self._embryo.tree)

    def _analyze_tree(self, tree, parent_path: str = ''):
        """
        Initializes `directory_paths`, `fpaths`, and `template_meta`. It
        returns a dict-based tree structure.
        """
        # TODO: Move the loading of nested embryos to an embryo method

        if not tree:
            return

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
                else:
                    # call _analyze_tree on subdirectory
                    child_path = join(parent_path, k)
                    self._analyze_tree(obj[k], child_path)
                    self.directory_paths.add(child_path)
            elif obj.endswith('/'):
                # it's an empty directory name
                dir_name = obj
                dir_path = join(parent_path, dir_name)
                self.directory_paths.add(dir_path)
            else:
                # it's a plain ol' file name
                fname = obj
                fpath = join(parent_path, fname)
                self.fpaths.add(fpath)
                if fpath in self._jinja2_templates:
                    # attempt to resolve the full path
                    self.template_meta[fpath] = {
                        'template_name': fpath,
                        'context_path': None,
                    }
                elif fname in self._jinja2_templates:
                    # top-level resolution of file name only
                    self.template_meta[fpath] = {
                        'template_name': fname,
                        'context_path': None,
                    }

    def _render_files(self, style_config):
        # Note that while we want the "loaded" context object in the pre, on,
        # and post-create methods, we want the "dumped" context in the
        # templates.
        schema = self._embryo.context_schema()
        dumped_context = self._embryo.dump()

        for fpath in self.fpaths:
            meta = self.template_meta.get(fpath)

            if meta is not None:
                tpl_name = meta['template_name']
                ctx_path = meta.get('context_path')
                ctx_obj = dumped_context

                # resolve context sub-object to pass into
                # the template as its context
                if ctx_path:
                    ctx_obj = get_nested_dict(dumped_context, ctx_path)

                # absolute file path for the rendered template
                abs_fpath = os.path.join(self.root, fpath.lstrip('/'))

                # inject the Embryo Python object into the context
                ctx_obj = deepcopy(ctx_obj)
                ctx_obj['embryo'] = self._embryo

                self._render_file(
                    abs_fpath, tpl_name, ctx_obj, style_config=style_config
                )

        return self.nested_embryos

    def _touch_filesystem(self) -> None:
        """
        Creates files and directories in the file system. This will not
        overwrite anything.
        """
        # TODO: Move this into the FileManager
        if not os.path.exists(self.root):
            os.makedirs(self.root)
            say('Creating directory: {path}', path=self.root)
        for dir_path in self.directory_paths:
            path = join(self.root, './{}'.format(dir_path))
            if not os.path.exists(path):
                say('Creating directory: {path}', path=path)
                os.makedirs(path)
        for fpath in self.fpaths:
            path = join(self.root, fpath)
            if not os.path.isfile(fpath) and not fpath.endswith('.embryo'):
                say('Touching file: {path}', path=fpath)
                open(path, 'a').close()

    def _render_file(
        self,
        abs_fpath: str,
        template_name: str,
        context: dict,
        style_config: dict = None
    ) -> None:
        """
        Renders a template to a file, provided that the `abs_fpath` provided is
        recognized by this `Renderer`.
        """
        try:
            template = self._jinja2_templates[template_name]
        except KeyError:
            raise TemplateNotFound(template_name)

        try:
            say('Rendering {p}', p=abs_fpath)
            rendered_text = template.render(context).strip()
        except Exception:
            shout('Problem rendering {p}', p=abs_fpath)
            raise

        if abs_fpath.endswith('.py'):
            style_config = style_config or STYLE_CONFIG
            try:
                formatted_text = FormatCode(
                    rendered_text, style_config=style_config
                )[0]
            except Exception:
                shout('Problem formatting {p}', p=abs_fpath)
                raise
        else:
            formatted_text = rendered_text

        self._write_file(abs_fpath, formatted_text)

    def _write_file(self, fpath: str, text: str) -> None:
        """
        Writes a string to a file, provided that the `fpath` provided is
        recognized by this `Renderer`.
        """
        abs_fpath = join(self.root, fpath.strip())
        with open(abs_fpath, 'w') as f_out:
            f_out.write(text)
