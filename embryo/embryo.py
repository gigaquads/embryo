import os
import yaml
import ujson
import json

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
from .utils import (
    say,
    shout,
    build_embryo_filepath,
    resolve_embryo_path,
    import_embryo,
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
    the context of running the Loader.
    """

    def __init__(self, path):
        self._path = path

        self.context = None
        self.tree = None
        self.templates = None

        # the jinja2 env is used in rendering filepath template strings
        # as well as the templatized tree.yml file.
        self.jinja_env = build_env()

        # the DotFileManager loads embryos corresponding to the contents of
        # .embryo/context.json files and provides an interface to them.
        self.dot = DotFileManager()

    def __repr__(self):
        return '<{class_name}({embryo_path})>'.format(
            class_name=self.__class__.__name__,
            embryo_path=self._path,
        )

    def load(self, context, from_fs=False):
        self.context = self._load_context(context, from_fs)

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
    def action(self):
        return self.context['embryo']['action']

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
        This method should be called only by Loader objects.
        """
        self.dot.load(self.destination)

        say('Running pre-create method...')
        self.pre_create()

    def apply_on_create(self, project: Project) -> None:
        say('Running on-create method...')
        self.on_create(project)

        # here is where we finally call load, following all places where the
        # running context object could have been dynamically modified.
        schema = self.context_schema()
        if schema:
            result = schema.load(self.context)
            if result.errors:
                shout('Failed to load context: {errors}', errors=json.dumps(
                    result.errors, indent=2, sort_keys=True
                ))
                exit(-1)
            self.context = result.data

        # now that we have the loaded context, dump it to build the tree
        dumped_context = schema.dump(self.context).data
        self.tree = self._load_tree(dumped_context)
        self.templates = self._load_templates(dumped_context)

    def apply_post_create(self, project: Project) -> None:
        """
        This method should be called only by Loader objects.
        """
        say('Running post-create method...')
        self.post_create(project)

    def _load_context(self, cli_kwargs: Dict = None, from_fs=False) -> Dict:
        """
        Context can come from three places and is merged into a computed dict
        in the following order:

            1. Data in the embryo's static context.json/yml file.
            2. Variables provided on the commandline interface, like --foo 1.
            3. Data provided from a file, named in the --context arg.
        """
        path = self._path
        fpath = build_embryo_filepath(path, 'context')
        context = Yaml.from_file(fpath) or {}

        # if a --context PATH_TO_JSON_FILE was provided on the CLI then try to
        # load that file and merge it into the existing context dict.
        cli_context_value = cli_kwargs.pop('context', None)
        if cli_context_value:
            if cli_context_value.endswith('.json'):
                with open(context_filepath) as context_file:
                    cli_context = ujson.load(context_file)
            elif cli_context_value.endswith('.yml'):
                cli_context = Yaml.from_file(context_filepath)
            else:
                # assume it's a JSON object string
                cli_context = ujson.loads(cli_context_value)

            context.update(cli_context)

        # we collect params used by Embryo creation into a separate "embryo"
        # subobject and add it to the context dict with setdefault so as not to
        # overwrite any user defined variable by the same name, "embryo":
        if not from_fs:
            context.setdefault(
                'embryo', {
                    'name': cli_kwargs.pop('embryo'),
                    'path': path,
                    'destination': os.path.abspath(cli_kwargs.pop('dest')),
                    'action': cli_kwargs.pop('action'),
                }
            )

        # Note that the remaining CLI kwargs should be custom context
        # variables, not Embryo creation parameters. We add these vars here.
        context.update(cli_kwargs)

        return context

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


class DotFileManager(object):
    """
    `DotFileManager` handles the loading of contents stored under the .embryo
    directories contained within the filesystem tree defined by an embryo. It
    provides a high-level interface for searching historical Embryo objects
    whose context data was discovered in .embryo/context.json files.
    """

    def __init__(self):
        self._embryo_search_path = build_embryo_search_path()
        self._embryo_name_path2embryos = defaultdict(list)
        self._embryo_name2embryos = defaultdict(list)
        self._path2embryos = defaultdict(list)

    def load(self, root: str) -> None:
        """
        To be run *after* the project is built. This loads all context.json
        files found in the filesystem, relative to a root directory. It imports
        and instantiates the Python Embryo objects corresponding to the persist
        context entries. This is called by the embryo `apply_on_create` method.
        """
        for path, subpaths, fnames in os.walk(root):
            json_fpath = os.path.join(path, '.embryo/context.json')
            if os.path.isfile(json_fpath):
                say('Reading {path}...', path=json_fpath)
            embryo_name2context_list = self._load_context_json(json_fpath)
            for embryo_name, context_list in embryo_name2context_list.items():
                count = len(context_list)
                say('Loading stored embryo: "{k}" ({n}x)...', k=embryo_name, n=count)
                for context in context_list:
                    embryo = self._load_embryo(context)
                    # the `path_key` is is the relative path to the current
                    # `path` directory, prepended with a '/'
                    path_key = '/' + path[len(root):]

                    # add the embryo to internal lookup tables:
                    self._embryo_name_path2embryos[embryo_name, path_key
                                                   ].append(embryo)
                    self._embryo_name2embryos[embryo_name].append(embryo)
                    self._path2embryos[path_key].append(embryo)

    def find(self, name: str = None, path: str = None) -> List[Embryo]:
        """
        Return a list of Embryo objects discovered in the filesystem tree
        relative to the root directory passed into the `load` method. Name or
        path or both can be specified. When both are specified, we return the
        Embryos with the given name within the given directory path.
        """
        if name and (not path):
            return self._embryo_name2embryos[name]
        elif (not name) and path:
            return self._path2embryos[path]
        elif name and path:
            return self._embryo_name_path2embryos[name, path]
        else:
            return []

    def _load_context_json(self, context_json_fpath: str) -> Dict:
        """
        Read in a context.json file to a dict.
        """
        loaded_json_obj = {}

        if os.path.isfile(context_json_fpath):
            with open(context_json_fpath) as fin:
                json_obj_str = fin.read()
                if json_obj_str:
                    loaded_json_obj = ujson.loads(json_obj_str)

        return loaded_json_obj

    def _load_embryo(self, context) -> Embryo:
        """
        Import and instantiate an Embryo object using a context dict loaded
        from a context.json file.
        """
        embryo_name = context['embryo']['name']
        embryo_path = resolve_embryo_path(
            self._embryo_search_path, embryo_name
        )
        embryo = import_embryo(embryo_path, context, True)
        return embryo
