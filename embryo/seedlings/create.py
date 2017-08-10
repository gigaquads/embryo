import os
import importlib
import argparse

import yaml

from embryo import Project


class SeedlingGenerator(object):

    def __init__(self):
        self.here = os.path.dirname(os.path.realpath(__file__))

    def create(self):
        args = self.parse_args()
        context = self.load_context(args.seedling)
        tree = self.load_tree_yaml(args.seedling)
        templates = self.import_templates(args.seedling)
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

    def import_templates(self, seedling: str):
        module_path = 'embryo.seedlings.{}.templates'.format(seedling)
        template_module = importlib.import_module(module_path)
        return template_module

    def load_tree_yaml(self, seedling: str):
        file_path = '{}/{}/tree.yml'.format(self.here, seedling)
        with open(file_path) as tree_file:
            tree_yml = tree_file.read()
            return tree_yml

    def load_context(self, seedling: str):
        file_path = '{}/{}/context.yml'.format(self.here, seedling)
        with open(file_path) as context_file:
            context = yaml.load(context_file)
            return context


if __name__ == '__main__':
    seedling_generator = SeedlingGenerator()
    seedling_generator.create()
