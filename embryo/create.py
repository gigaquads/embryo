import os
import re
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
        project = Project(root=args.name, tree=tree, templates=templates)
        project.build(context)

    def parse_args(self):
        parser = argparse.ArgumentParser()
        embryo_names = [
            x for x in os.listdir(self.embryos_dir)
            if os.path.isdir(self.embryos_dir + '/' + x)
            ]
        parser.add_argument('embryo', type=str, help='''
            The name of the embryo to generate. Built-ins include: {}.
            '''.format(', '.join(embryo_names)))
        parser.add_argument('--name', type=str, required=True, help='''
            The name of the project you're creating.
            ''')
        return parser.parse_args()

    def load_templates(self, embryo: str):
        templates_dir = '{}/templates'.format(self.embryo_path)
        templates = {}
        for file_name in os.listdir(templates_dir):
            with open('{}/{}'.format(templates_dir, file_name)) as f_in:
                templates[file_name] = f_in.read()
        return templates

    def load_tree_yaml(self, embryo: str, context: dict):
        file_path = '{}/tree.yml'.format(self.embryo_path)
        with open(file_path) as tree_file:
            tree_yml_tpl = tree_file.read()
            tree_yml = Template(tree_yml_tpl).render(context)
            return tree_yml

    def load_context(self, args):
        file_path = '{}/context.yml'.format(self.embryo_path)
        with open(file_path) as context_file:
            context = yaml.load(context_file)
            context.update({
                'embryo_name': args.embryo,
                'project_name': args.name,
                'project_name_snake_case': re.sub(
                    r'([a-z])([A-Z])', r'\1_\2', args.name).lower(),
                })
            return context


if __name__ == '__main__':
    embryo_generator = EmbryoGenerator()
    embryo_generator.create()
