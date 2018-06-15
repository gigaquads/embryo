import os
import sys
import re
import traceback
import inspect
import importlib
import argparse
import json

from jinja2 import Template

from embryo import Project
from appyratus.types import Yaml

from .hooks import HookManager
from .exceptions import EmbryoNotFound, TemplateLoadFailed
from .environment import build_env
from .embryo import Embryo


class EmbryoGenerator(object):
    """
    Evaluates and generates an embryo project.
    """

    @classmethod
    def log(cls, fstr, *args, **kwargs):
        print('>>> ' + fstr.format(*args, **kwargs))

    @classmethod
    def from_args(cls, args):
        context = {
            k: getattr(args, k)
            for k in dir(args) if not k.startswith('_')
        }
        return cls().create(name=context['embryo'], context=context)

    def __init__(self):
        self.env = build_env()
        self.here = os.path.dirname(os.path.realpath(__file__))
        self.embryos_dir = '{}/embryos'.format(self.here)
        self.embryo_path = None
        self.embryo_search_path = [os.getcwd()]
        if 'EMBRYO_PATH' in os.environ:
            path = os.environ['EMBRYO_PATH']
            self.embryo_search_path.extend(path.split(':'))

    def create(self, name: str, dest: str = None, context: dict = None):
        embryo_path = self._resolve_embryo_path(name)  # <- sets self.embryo_path
        hooks = self._load_hooks()  # XXX: deprecated
        embryo = self._load_embryo_object(name)
        deps = self._load_deps()
        context = self._load_context(name, hooks, embryo, context)
        tree = self._load_tree_yaml(name, context)
        templates = self._load_templates(name, context)
        project = self._build_project(context, dest, tree, templates, hooks, embryo, deps)

    def _resolve_embryo_path(self, name):
        if inspect.ismodule(name):
            self.embryo_path = name.__path__._path[0]
        elif '/' in name:
            self.embryo_path = name
        else:
            for path in self.embryo_search_path:
                embryo_path = '{}/{}'.format(path.rstrip('/'), name)
                if os.path.exists(embryo_path):
                    self.embryo_path = embryo_path
                    break

        if not self.embryo_path:
            raise EmbryoNotFound(name)

        # ensure the embryo_path is absolute and add to python path
        self.embryo_path = os.path.realpath(self.embryo_path)
        sys.path.append(self.embryo_path)

        return self.embryo_path

    def _build_project(self, context, root, tree, templates, hooks, embryo, deps):
        self.log('Creating embryo...')
        self.log('Context:')
        self.log(json.dumps(context, indent=2, sort_keys=True))

        project = Project(
            root=(root or './'),
            tree=tree,
            templates=templates,
            deps=deps
        )

        project.build(context)

        if hooks.post_create:  # XXX: deprecated
            self.log('(DEPRECATED) Running post_create hook...')
            hooks.post_create(project, context)

        if embryo:
            self.log('Running Embryo.post_create hook...')
            embryo.apply_post_create(project, context)

        return project

    def _load_templates(self, embryo: str, context: dict = None):
        templates_dir = os.path.join(self.embryo_path, 'templates')
        templates = {}

        if not os.path.isdir(templates_dir):
            return templates

        for root, dirs, files in os.walk(templates_dir):
            for file_name in files:
                if file_name.endswith('.swp'):
                    continue
                file_path = os.path.join(root, file_name)
                rel_path = file_path.replace(templates_dir, '').lstrip('/')
                render_path = self.env.from_string(rel_path).render(context)

                with open(file_path) as f_in:
                    try:
                        templates[render_path] = f_in.read()
                    except Exception as exc:
                        raise TemplateLoadFailed(file_path)

        return templates

    def _load_deps(self):
        file_path = os.path.join(self.embryo_path, 'deps.yml')
        data = Yaml.from_file(file_path)
        return data

    def _load_tree_yaml(self, embryo: str, context: dict):
        file_path = os.path.join(self.embryo_path, 'tree.yml')
        with open(file_path) as tree_file:
            tree_yml_tpl = tree_file.read()
            tree_yml = self.env.from_string(tree_yml_tpl).render(context)
            return tree_yml

    def _load_context(self, name: str, hooks, embryo, data: dict = None):
        file_path = '{}/context.yml'.format(self.embryo_path)
        context = Yaml.from_file(file_path)

        if not context:
            context = {}

        context.update(data)
        #context.update({'embryo_name': name, 'args': data})

        context_filepath = getattr(data, 'context', None)
        if context_filepath:
            if context_filepath.endswith('.json'):
                with open(context_filepath) as context_file:
                    data = json.load(context_file)
            elif context_filepath.endswith('.yml'):
                data = Yaml.from_file(context_filepath)

            context.update(data)

        if hooks.pre_create:  # XXX: deprecated
            self.log('(DEPRECATED) Running pre_create hook...')
            hooks.pre_create(context)

        if embryo:
            self.log('Running Embryo.pre_create hook...')
            context = embryo.apply_pre_create(context)

        return context

    def _load_embryo_object(self):
        embryo = None
        abs_filepath = os.path.join(self.embryo_path, 'embryo.py')
        if os.path.isfile(abs_filepath):
            module = importlib.import_module('embryo')
            for obj in inspect.getmembers(module, inspect.isclass):
                if issubclass(obj, Embryo):
                    embryo = obj()
        return embryo

    def _load_hooks(self):
        abs_filepath = os.path.join(self.embryo_path, 'hooks.py')
        if os.path.isfile(abs_filepath):
            self.log('(DEPRECATED) Loading hooks.py')
            module = importlib.import_module('hooks')
            hook_manager = HookManager(
                pre_create=getattr(module, 'pre_create', None),
                post_create=getattr(module, 'post_create', None),
            )
        else:
            hook_manager = HookManager()

        return hook_manager


if __name__ == '__main__':
    embryo_generator = EmbryoGenerator()
    embryo_generator.create()
