import os
import re
import traceback
import importlib
import argparse

import yaml

from jinja2 import Template

from embryo import Project


class EmbryoGenerator(object):

    def __init__(self):
        self.here = os.path.dirname(os.path.realpath(__file__))
        self.embryos_dir = '{}/embryos'.format(self.here)
        self.embryo_path = None
        self.embryo_search_path = [
            os.getcwd(),
            self.embryos_dir,
            ]

    def create(self):
        args = self.parse_args()

        if '/' in args.embryo:
            self.embryo_path = args.embryo
        else:
            for path in self.embryo_search_path:
                embryo_path = '{}/{}'.format(path, args.embryo)
                if os.path.exists(embryo_path):
                    self.embryo_path = embryo_path
                    break

        context = self.load_context(args)
        tree = self.load_tree_yaml(args.embryo, context)
        templates = self.load_templates(args.embryo)
        hooks = self.load_hooks()
        project = Project(root=args.name, tree=tree, templates=templates)

        if hooks.pre_create:
            hooks.pre_create(project, context, tree, templates)

        project.build(context)

        if hooks.post_create:
            hooks.post_create(project, context)

    def parse_args(self):
        embryo_names = [
            x for x in os.listdir(self.embryos_dir)
            if os.path.isdir(self.embryos_dir + '/' + x)
            ]

        parser = argparse.ArgumentParser()
        parser.add_argument('embryo', type=str, help='''
            The name of the embryo to generate. Built-ins include: {}.
            '''.format(', '.join(embryo_names)))
        parser.add_argument('--destination', type=str, help='''
            A file path to the directory where the embryo should be generated.
            '''.format(', '.join(embryo_names)))
        parser.add_argument('--name', type=str, default='', help='''
            The name of the project you're creating.
            ''')

        args, unknown = parser.parse_known_args()

        # now combine known and unknown arguments into a single dict
        args_dict = {
            k: getattr(args, k) for k in dir(args) if not k.startswith('_')
            }

        for i in range(0, len(unknown), 2):
            k = unknown[i]
            v = unknown[i+1]
            args_dict[k.lstrip('-')] = v

        # build a custom type with the combined argument names as attributes
        arguments = type('Arguments', (object, ), args_dict)()

        return arguments

    def load_templates(self, embryo: str):
        templates_dir = '{}/templates'.format(self.embryo_path)
        templates = {}

        if not os.path.isdir(templates_dir):
            return templates

        for file_name in os.listdir(templates_dir):
            if file_name.endswith('.swp'):
                continue
            with open('{}/{}'.format(templates_dir, file_name)) as f_in:
                try:
                    templates[file_name] = f_in.read()
                except Exception as exc:
                    print('failed to load {} template'.format(file_name))
                    raise exc

        return templates

    def load_tree_yaml(self, embryo: str, context: dict):
        file_path = '{}/tree.yml'.format(self.embryo_path)
        with open(file_path) as tree_file:
            tree_yml_tpl = tree_file.read()
            tree_yml = Template(tree_yml_tpl).render(context)
            return tree_yml

    def load_context(self, args):
        file_path = '{}/context.yml'.format(self.embryo_path)

        if not os.path.exists(file_path):
            context = {}
        else:
            with open(file_path) as context_file:
                context = yaml.load(context_file)

        context.update({
            'args': {
                k: getattr(args, k) for k in dir(args) if not k.startswith('_')
                },
            'embryo_name': args.embryo,  # XXX: use of these is deprecated
            'project_name': args.name,
            'project_name_snake_case': re.sub(
                r'([a-z])([A-Z])', r'\1_\2', args.name).lower(),
            })

        return context

    def load_hooks(self):
        old_cwd = os.getcwd()
        os.chdir(self.embryo_path)

        if os.path.isfile('hooks.py'):
            module = importlib.import_module('hooks')
            hook_manager = HookManager(
                pre_create=getattr(module, 'pre_create', None),
                post_create=getattr(module, 'post_create', None),
                )
        else:
            hook_manager = HookManager()

        os.chdir(old_cwd)
        return hook_manager


class HookManager(object):

    def __init__(self, pre_create=None, post_create=None):
        self.pre_create = pre_create
        self.post_create = post_create


if __name__ == '__main__':
    embryo_generator = EmbryoGenerator()
    embryo_generator.create()
