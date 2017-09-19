import os
import sys
import re
import traceback
import importlib
import argparse

import yaml

from pprint import pprint

from jinja2 import Template

from embryo import Project

from .exceptions import TemplateNotFound
from .environment import build_env


class EmbryoGenerator(object):
    def __init__(self):
        self.env = build_env()
        self.here = os.path.dirname(os.path.realpath(__file__))
        self.embryos_dir = '{}/embryos'.format(self.here)
        self.embryo_path = None
        self.embryo_search_path = [os.getcwd()]
        if 'EMBRYO_PATH' in os.environ:
            path = os.environ['EMBRYO_PATH']
            self.embryo_search_path.extend(path.split(':'))

    def create(self, args):
        self.args = args
        if '/' in args.embryo:
            self.embryo_path = args.embryo
        else:
            for path in self.embryo_search_path:
                embryo_path = '{}/{}'.format(path.rstrip('/'), args.embryo)
                if os.path.exists(embryo_path):
                    self.embryo_path = embryo_path
                    break

        # ensure the embryo_path is absolute
        self.embryo_path = os.path.realpath(self.embryo_path)

        sys.path.append(self.embryo_path)

        context = self.load_context(args)
        hooks = self.load_hooks()

        if hooks.pre_create:
            print('>>> Running pre_create hook...')
            hooks.pre_create(context)

        tree = self.load_tree_yaml(args.embryo, context)
        templates = self.load_templates(args.embryo, context)

        print('>>> Creating embryo...')
        print('-' * 80)
        print('>>> Context:')

        pprint(context, indent=2)

        root = args.destination
        project = Project(root=root, tree=tree, templates=templates)

        project.build(context)

        if hooks.post_create:
            print('>>> Running post_create hook...')
            hooks.post_create(project, context)

    def load_templates(self, embryo: str, context: dict=None):
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

    def load_tree_yaml(self, embryo: str, context: dict):
        file_path = os.path.join(self.embryo_path, 'tree.yml')
        with open(file_path) as tree_file:
            tree_yml_tpl = tree_file.read()
            tree_yml = self.env.from_string(tree_yml_tpl).render(context)
            return tree_yml

    def load_context(self, args):
        file_path = '{}/context.yml'.format(self.embryo_path)

        if not os.path.exists(file_path):
            context = {}
        else:
            with open(file_path) as context_file:
                context = yaml.load(context_file)
            if not context:
                context = {}

        context.update({
            'args':
            {k: getattr(args, k)
             for k in dir(args) if not k.startswith('_')},
            'embryo_name': args.embryo,  # XXX: use of these is deprecated
            'project_name': args.name,
        })

        context_filepath = getattr(args, 'context', None)
        if context_filepath:
            if context_filepath.endswith('.json'):
                with open(context_filepath) as context_file:
                    data = json.load(context_file)
            elif context_filepath.endswith('.yml'):
                with open(context_filepath) as context_file:
                    data = yaml.load(context_file)

            context.update(data)

        return context

    def load_hooks(self):
        abs_filepath = os.path.join(self.embryo_path, 'hooks.py')
        if os.path.isfile(abs_filepath):
            module = importlib.import_module('hooks')
            hook_manager = HookManager(
                pre_create=getattr(module, 'pre_create', None),
                post_create=getattr(module, 'post_create', None), )
        else:
            hook_manager = HookManager()

        return hook_manager


class HookManager(object):
    def __init__(self, pre_create=None, post_create=None):
        self.pre_create = pre_create
        self.post_create = post_create


if __name__ == '__main__':
    embryo_generator = EmbryoGenerator()
    embryo_generator.create()
