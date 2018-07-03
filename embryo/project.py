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

from .constants import RE_RENDERING_METADATA, RE_RENDERING_EMBRYO, STYLE_CONFIG
from .environment import build_env
from .exceptions import TemplateNotFound
from .utils import say, shout


class Project(object):
    """
    A `Project`  is responsible for taking the loaded instructions owned by an
    `Embryo` object and generating files into the filesystem.
    """

    _json_encoder = JsonEncoder()

    def __init__(self, embryo: 'Embryo'):
        """
        Initialize a project
        """
        self.root = embryo.destination.rstrip('/')
        self.fpaths = set()
        self.directory_paths = set()
        self.template_meta = {}
        self.nested_embryos = []
        self.dot_embryo_path = os.path.join(self.root, '.embryo')
        self.embryo = embryo

        # these are initialized in the build method:
        self.tree = None
        self.templates = None

    def _build_jinja2_templates(self, templates):
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

    def _analyze_tree(self, tree, parent_path: str = '') -> dict:
        """
        Initializes `directory_paths`, `fpaths`, and `template_meta`. It
        returns a dict-based tree structure.
        """
        if isinstance(tree, str):
            tree = yaml.load(tree)

        result = {}

        if not tree:
            return result

        for obj in tree:
            if isinstance(obj, dict):
                k = list(obj.keys())[0]
                v = obj[k]
                if isinstance(v, str):
                    # in this case, we have a file name or nested embryo with
                    # associated template rendering metadata we must parse out.
                    if k == 'embryo':
                        # embryo:falcon_app(foo)
                        match = RE_RENDERING_EMBRYO.match(v)
                        nested_embryo_name, ctx_key = match.groups()
                        self.nested_embryos.append(
                            {
                                'embryo_name': nested_embryo_name,
                                'context_path': ctx_key,
                                'dir_path': parent_path,
                            }
                        )
                    else:
                        match = RE_RENDERING_METADATA.match(v)
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
                    # call _analyze_tree on subdirectory
                    child_path = join(parent_path, k)
                    if child_path == '.embryo':
                        self.dot_embryo_path = child_path
                    result[k] = self._analyze_tree(obj[k], child_path)
                    self.directory_paths.add(child_path)
            elif obj.endswith('/'):
                # it's an empty directory name
                dir_name = obj
                dir_path = join(parent_path, dir_name)
                self.directory_paths.add(dir_path)
                result[dir_name] = False
                if dir_name == '.embryo':
                    self.dot_embryo_path = dir_path
            else:
                # it's a plain ol' file name
                fname = obj
                fpath = join(parent_path, fname)
                if fname == '.embryo':
                    self.dot_embryo_path = fpath
                else:
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

    def build(self, style_config: Dict = None) -> None:
        """
        # Args
        - embryo: the Embryo object
        - context: a context dict for use by jinja2 templates.
        - style_config: yapf style options for code formating>

        1. Create the directories and files in the file system.
        2. Render templates into said files.
        """
        say('Stimulating embryonic growth sequence...')
        say('Hatching Embryo: "{name}"', name=self.embryo.name)
        say('Embryo Location: {path}', path=self.embryo.path)
        say('Destination: {dest}', dest=self.embryo.destination)

        self.embryo.apply_on_create(self)

        # create the project file structure
        self.templates = self._build_jinja2_templates(self.embryo.templates)
        self.tree = self._analyze_tree(self.embryo.tree)

        self.touch()

        # insert context into .embryo/context.json file
        self._persist_context()

        say('Template Context:\n\n{ctx}\n', ctx=json.dumps(
            json.loads(self._json_encoder.encode(self.embryo.context)),
            indent=2, sort_keys=True
        ))

        say('Tree:\n\n{tree}', tree='\n'.join(
            ' ' * 4 + line for line in yaml.dump(
                self.embryo.tree,
                explicit_start=False,
                explicit_end=False,
                default_flow_style=False,
                indent=2,
            ).split('\n')
        ))

        # Note that while we want the "loaded" context object in the pre, on,
        # and post-create methods, we want the "dumped" context in the
        # templates.
        schema = self.embryo.context_schema()
        dumped_context = self.embryo.dump()

        for fpath in self.fpaths:
            meta = self.template_meta.get(fpath)

            if meta is not None:
                tpl_name = meta['template_name']
                ctx_path = meta.get('context_path')
                ctx_obj = dumped_context

                # result the context sub-object to pass into
                # the template as its context
                if ctx_path:
                    for k in ctx_path.split('.'):
                        ctx_obj = ctx_obj[k]

                # absolute file path for the rendered template
                abs_fpath = os.path.join(self.root, fpath.lstrip('/'))

                # inject the Embryo Python object into the context
                ctx_obj = deepcopy(ctx_obj)
                ctx_obj['embryo'] = self.embryo

                self.render(
                    abs_fpath, tpl_name, ctx_obj, style_config=style_config
                )

        return self.nested_embryos

    def _persist_context(self) -> None:
        """
        Appnd the context dict to the .embryo/context.json object.
        """
        embryo = self.embryo
        dot_embryo_path = self.dot_embryo_path
        context_json_path = os.path.join(dot_embryo_path, 'context.json')
        embryo_name_2_contexts = {}

        # create or load the .embryo/ dir in the "root" dir
        if not os.path.isdir(dot_embryo_path):
            say('Creating .embryo directory: {path}', path=dot_embryo_path)
            os.mkdir(dot_embryo_path)

        # load the JSON file
        if os.path.isfile(context_json_path):
            # read in the current data structure
            with open(context_json_path, 'r') as fin:
                json_str = fin.read()
                if json_str:
                    embryo_name_2_contexts = json.loads(json_str)

        # adding to the JSON file data by adding it to the list of other
        # embryos generated here of the same name.
        schema = embryo.context_schema()
        if schema:
            context = schema.dump(embryo.context, strict=True).data

        if embryo.name not in embryo_name_2_contexts:
            embryo_name_2_contexts[embryo.name] = [embryo.context]
        else:
            embryo_name_2_contexts[embryo.name].append(embryo.context)

        # write the appended data back to the JSON file
        with open(context_json_path, 'w') as fout:
            say('Appending {path}', path=context_json_path)
            fout.write(
                json.dumps(
                    json.loads(
                        self._json_encoder.encode(embryo_name_2_contexts)
                    ), indent=2, sort_keys=True
                ) + '\n'
            )

    def touch(self) -> None:
        """
        Creates files and directories in the file system. This will not
        overwrite anything.
        """
        if not os.path.exists(self.root):
            os.makedirs(self.root)
            say('Creating directory: {path}', path=self.root)
        for dir_path in self.directory_paths:
            path = join(self.root, './{}'.format(dir_path))
            if not os.path.exists(path):
                say('Creating directory: {path}', path=path)
                os.makedirs(path)
        for fpath in self.fpaths:
            path = join(self.root, './{}'.format(fpath))
            if not os.path.isfile(fpath):
                say('Touching file: {path}', path=fpath)
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
