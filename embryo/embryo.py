import os
import json
import inspect

import ujson
import yaml

from typing import Dict, List
from collections import defaultdict

from jinja2 import Template
from jinja2.exceptions import TemplateSyntaxError

from appyratus.validation import Schema
from appyratus.validation import fields
from appyratus.types import Yaml

from .project import Project
from .environment import build_env
from .exceptions import TemplateLoadFailed
from .constants import EMBRYO_FILE_NAMES
from .relationship import Relationship, RelationshipManager
from .file_manager import (
    FileTypeAdapter,
    JsonAdapter,
    YamlAdapter,
    FileManager,
)
from .dot import DotFileManager
from .utils import (
    say,
    shout,
    build_embryo_filepath,
    resolve_embryo_path,
    import_embryo_class,
    build_embryo_search_path,
)


class ContextSchema(Schema):
    """
    Returns an instance of a Schema class, which is applied to the context
    dict, using schema.load(context). A return value of None skips this
    process, i.e. it is optional.
    """
    embryo = fields.Object(
        {
            'timestamp': fields.DateTime(),
            'name': fields.Str(),
            'action': fields.Str(),
            'path': fields.Str(),
            'destination': fields.Str(),
        }
    )


class Embryo(object):
    """
    Embryo objects serve as an interface to performing various actions within
    the context of running the Incubator.
    """

    Schema = ContextSchema

    def __init__(self, path: str, context: Dict):
        self._path = path
        self._context = self._load_context(context)
        self._schema = self.context_schema()
        self.templates = None
        self.tree = None

        # the jinja2 env is used in rendering filepath template strings
        # as well as the templatized tree.yml file.
        self.jinja_env = build_env()

        # the DotFileManager loads embryos corresponding to the contents of
        # .embryo/context.json files and provides an interface to them.
        self.dot = DotFileManager()

        # Mapping from embryo name to an Embrryo object or List[Embryo].
        # This dict is initialized by a RelationshipManager in pre_create.
        self._related = {}

        self._fs = FileManager()

    def __repr__(self):
        return '<{class_name}({embryo_path})>'.format(
            class_name=self.__class__.__name__,
            embryo_path=self._path,
        )

    @property
    def adapters(self) -> List[FileTypeAdapter]:
        return [
            JsonAdapter(indent=2, sort_keys=True),
            YamlAdapter(multi=True),
        ]

    @property
    def related(self):
        return self._related

    @property
    def context(self):
        return self._context

    @property
    def fs(self):
        return self._fs

    @property
    def path(self):
        return self._path

    @property
    def name(self):
        return self.context['embryo']['name']

    @property
    def destination(self):
        return self.context['embryo']['destination']

    @property
    def timestamp(self):
        return self.context['embryo']['timestamp']

    @staticmethod
    def context_schema():
        """
        Returns an instance of a Schema class, which is applied to the context
        dict, using schema.load(context). A return value of None skips this
        process, i.e. it is optional.
        """
        return ContextSchema()

    def pre_create(self) -> None:
        """
        Perform any side-effects or preprocessing before the embryo Project and
        related objects are created. if a context_schema exists, the `context`
        argument is the marshaled result of calling `schema.load(context)`.
        This method should be overriden.
        """

    def on_create(self, project: Project) -> None:
        """
        This logic follows the rendering of the tree.yml and templatized file
        paths. At this point, we have access to stored filesystem context.
        """

    def post_create(self, project: Project) -> None:
        """
        Post_create is called upon the successful creation of the Project
        object. Any side-effects following the creation of the embryo in the
        filesystem can be performed here. This method should be overriden.
        """

    def apply_pre_create(self) -> None:
        """
        This method should be called only by Incubator objects.
        """
        self.dot.load(self)

        # Load the related dot-embryos and add them to context for the sake of
        # accessing inherited data, like a project's name stored in a
        # previously-run "new project" Embryo context.
        self._related = RelationshipManager().load(self)

        say('Running pre-create method...')
        self.pre_create()

    def apply_on_create(self, project: Project) -> None:
        # Here is where we finally call load, following all places where the
        # running context object could have been dynamically modified.
        schema = self.context_schema()
        if schema:
            result = schema.load(self.context)
            if result.errors:
                shout(
                    'Failed to load context: {errors}',
                    errors=json.dumps(result.errors, indent=2, sort_keys=True)
                )
                exit(-1)
            self._context = result.data

        # now that we have the loaded context, dump it to build the tree
        dumped_context = self.dump()

        self.tree = self._load_tree(dumped_context)
        self.templates = self._load_templates(dumped_context)

        self._fs.read(self)

        say('Running on-create method...')
        self.on_create(project)

    def dump(self):
        """
        Dump schema to context and update with related attributes
        """
        dumped_context = self._schema.dump(self.context).data
        dumped_context.update(self._related)
        return dumped_context

    def apply_post_create(self, project: Project) -> None:
        """
        This method should be called only by Incubator objects.
        """
        self._fs.write()

        say('Running post-create method...')
        self.post_create(project)

    def _load_context(self, context: Dict = None) -> Dict:
        """
        Context can come from three places and is merged into a computed dict
        in the following order:

            1. Data in the embryo's static context.json/yml file.
            2. Variables provided on the commandline interface, like --foo 1.
            3. Data provided from a file, named in the --context arg.
        """
        path = self._path
        fpath = build_embryo_filepath(path, 'context')

        dynamic_context = context
        static_context = Yaml.from_file(fpath) or {}

        merged_context = {}
        merged_context.update(static_context)
        merged_context.update(dynamic_context)

        return merged_context

    def _load_templates(self, context: Dict):
        """
        Read all template file. Each template string is stored in a dict, keyed
        by the relative path at which it exists, relative to the templates root
        directory. The file paths themselves are templatized and are therefore
        rendered as well in this procedure.
        """
        templates_path = build_embryo_filepath(self._path, 'templates')
        templates = {}

        if not os.path.isdir(templates_path):
            return templates

        for root, dirs, files in os.walk(templates_path):
            for fname in files:
                if fname.endswith('.swp'):
                    continue

                # the file path may itself be templatized. here, we render the
                # filepath template using the context dict and read in the
                # template files.

                # fpath here is the templatized file path to the template
                fpath = os.path.join(root, fname)

                # rel_fpath is the path relative to the root templates dir
                rel_fpath = fpath.replace(templates_path, '').lstrip('/')

                # fname_template is the jinja2 Template for the rel_fpath str
                try:
                    fname_template = self.jinja_env.from_string(rel_fpath)
                except TemplateSyntaxError:
                    shout(
                        'Could not render template '
                        'for file path string: {p}',
                        p=fpath
                    )
                    raise

                # finally rendered_rel_fpath is the rendered relative path
                rendered_rel_fpath = fname_template.render(context)

                # now actually read the file into the resulting dict.
                with open(fpath) as fin:
                    try:
                        templates[rendered_rel_fpath] = fin.read()
                    except Exception:
                        raise TemplateLoadFailed(fpath)

        return templates

    def _load_tree(self, context: Dict) -> Dict:
        """
        Read and deserialized the file system tree yaml file as well as render
        it, as it is a templatized file.
        """
        fpath = build_embryo_filepath(self._path, 'tree')
        with open(fpath) as tree_file:
            tree_yml_tpl = tree_file.read()
            tree_yml = self.jinja_env.from_string(tree_yml_tpl).render(context)
            return yaml.load(tree_yml)
