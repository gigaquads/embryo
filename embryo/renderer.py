import os
from collections import defaultdict
from copy import deepcopy
from os.path import join
from types import ModuleType
from typing import (
    Text,
    Dict,
    List,
)

import yaml

from appyratus.files import (
    PythonModule,
    Yaml,
    Json,
)
from appyratus.utils import (
    PathUtils,
    Template,
)

from .constants import (
    RE_RENDERING_EMBRYO,
    RE_RENDERING_METADATA,
    STYLE_CONFIG,
)
from .environment import build_env
from .exceptions import TemplateNotFound
from .utils import (
    say,
    shout,
)


class Renderer(object):
    """
    A `Renderer`  is responsible for taking the loaded instructions owned by an
    `Embryo` object and generating files into the filesystem.
    """

    def __init__(self):
        """
        Initialize a renderer
        """
        self.embryo = None
        self.root = None
        self.fpaths = set()
        self.directory_paths = set()
        self.template_meta = {}
        self.nested_embryos = []
        self.tree = None
        self.jinja2_templates = None

    def render(self, embryo: 'Embryo', style_config: Dict = None) -> None:
        """
        # Args
        - embryo: the Embryo object
        - context: a context dict for use by jinja2 templates.
        - style_config: yapf style options for code formating.

        1. Create the directories and files in the file system.
        2. Render templates into said files.
        """
        self.embryo = embryo
        self.root = embryo.destination.rstrip('/')

        self._buildjinja2_templates()
        self._analyze_embryo()

        say(
            'Context:\n\n{ctx}\n',
            ctx=Json.dump(self.embryo.context, indent=2, sort_keys=True)
        )

        say(
            'Tree:\n\n{tree}',
            tree='\n'.join(
                ' ' * 4 + line for line in yaml.dump(
                    self.embryo.tree,
                    default_flow_style=False,
                    indent=2,
                ).split('\n')
            )
        )

        self.embryo.fs._touch_filesystem(self.root, self.directory_paths, self.fpaths)
        self._render_files(style_config)
        self.embryo.persist()

    def _buildjinja2_templates(self):
        """
        Load template files from a templates module, ignoring any "private"
        object starting with an _. Return a dict, mapping each Template
        object's name to the object.
        """
        templates = self.embryo.templates

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
                say('Loading template: {}'.format(k))
                if isinstance(v, Template):
                    loaded_templates[k] = v
                elif isinstance(v, str):
                    try:
                        loaded_templates[k] = jinja_env.from_string(v)
                    except Exception as exc:
                        source = exc.source.split('\n')[exc.lineno - 1]
                        shout(
                            'Error "{message}", line {line} {source}'.format(
                                message=exc.message, line=exc.lineno, source=source
                            )
                        )

        self.jinja2_templates = loaded_templates

    def _analyze_embryo(self):
        self._analyze_tree(self.embryo.tree)

    def _analyze_tree(self, tree, parent_path: Text = ''):
        """
        Initializes `directory_paths`, `fpaths`, and `template_meta`. It
        returns a dict-based tree structure.
        """
        # TODO: Move the loading of nested embryos to an embryo method

        if not tree:
            return

        for obj in tree:
            if obj is None:
                # an empty node, do nothing
                continue
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
                if fpath in self.jinja2_templates:
                    # attempt to resolve the full path
                    self.template_meta[fpath] = {
                        'template_name': fpath,
                        'context_path': None,
                    }
                elif fname in self.jinja2_templates:
                    # top-level resolution of file name only
                    self.template_meta[fpath] = {
                        'template_name': fname,
                        'context_path': None,
                    }

    def _render_files(self, style_config):
        # Note that while we want the "loaded" context object in the pre, on,
        # and post-create methods, we want the "dumped" context in the
        # templates.
        schema = self.embryo.context_schema()
        dumped_context = self.embryo.dumped_context

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
                ctx_obj.update(self.embryo.related)
                ctx_obj['embryo'] = self.embryo

                self._render_file(abs_fpath, tpl_name, ctx_obj, style_config=style_config)

        return self.nested_embryos

    def render_template(
        self,
        template_name: Text,
        context: Dict,
    ) -> None:
        rendered_text = None
        try:
            template = self.jinja2_templates[template_name]
        except KeyError:
            raise TemplateNotFound(template_name)

        try:
            say('Rendering {t}', t=template_name)
            rendered_text = template.render(context).strip()
        except Exception:
            shout('Problem rendering {t}', t=template_name)
            raise
        return rendered_text

    def _render_file(
        self,
        abs_fpath: Text,
        template_name: Text,
        context: Dict,
        style_config: Dict = None
    ) -> None:
        """
        Renders a template to a file, provided that the `abs_fpath` provided is
        recognized by this `Renderer`.
        """
        try:
            say('Rendering template {p}', p=abs_fpath)
            rendered_text = self.render_template(
                template_name=template_name, context=context
            )
        except Exception:
            shout('Problem rendering {p}', p=abs_fpath)
            raise

        formatted_text = rendered_text
        # get the full filepath with root prefix
        fpath = self.get_abs_path(abs_fpath)
        # load up the adapter for the file
        adapter = self.get_adapter(fpath)
        loaded_text = adapter.load(formatted_text)
        # write the loaded data
        adapter.write(fpath, loaded_text)

    def get_abs_path(self, fpath):
        return join(self.root, fpath.strip())

    def get_adapter(self, fpath):
        ext = PathUtils.get_extension(fpath)
        adapter = self.embryo.ext2adapter.get(ext if ext is None else None)
        return adapter
