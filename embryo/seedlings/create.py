import os
import re
import importlib
import argparse

import yaml

from jinja2 import Template

from embryo import Project


class SeedlingGenerator(object):

    def __init__(self):
        self.here = os.path.dirname(os.path.realpath(__file__))
        self.seedling_path = None
        self.seedling_search_path = [
            os.getcwd(),
            self.here,
            ]

    def create(self):
        args = self.parse_args()

        if '/' in args.seedling:
            self.seedling_path = args.seedling
        else:
            for path in self.seedling_search_path:
                seedling_path = '{}/{}'.format(path, args.seedling)
                if os.path.exists(seedling_path):
                    self.seedling_path = seedling_path
                    break

        context = self.load_context(args)
        tree = self.load_tree_yaml(args.seedling, context)
        templates = self.load_templates(args.seedling)
        project = Project(root=args.name, tree=tree, templates=templates)
        project.build(context)

    def parse_args(self):
        parser = argparse.ArgumentParser()
        parser.add_argument('--seedling', type=str, required=True, help='''
            The name of the seedling to generate. See contents of {}.
            '''.format(self.here))
        parser.add_argument('--name', type=str, required=True, help='''
            The name of the project you're creating.
            ''')
        return parser.parse_args()

    def load_templates(self, seedling: str):
        templates_dir = '{}/templates'.format(self.seedling_path)
        templates = {}
        for file_name in os.listdir(templates_dir):
            with open('{}/{}'.format(templates_dir, file_name)) as f_in:
                templates[file_name] = f_in.read()
        return templates

    def load_tree_yaml(self, seedling: str, context: dict):
        file_path = '{}/tree.yml'.format(self.seedling_path)
        with open(file_path) as tree_file:
            tree_yml_tpl = tree_file.read()
            tree_yml = Template(tree_yml_tpl).render(context)
            return tree_yml

    def load_context(self, args):
        file_path = '{}/context.yml'.format(self.seedling_path)
        with open(file_path) as context_file:
            context = yaml.load(context_file)
            context['seedling'] = {
                'seedling_name': args.seedling,
                'project_name': args.name,
                'project_name_snake_case': re.sub(
                    r'([a-z])([A-Z])', r'\1_\2', args.name).lower(),
                }
            return context


if __name__ == '__main__':
    seedling_generator = SeedlingGenerator()
    seedling_generator.create()
