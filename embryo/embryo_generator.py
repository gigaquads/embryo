import os
import inspect
import importlib
import json
import yaml

from typing import Dict, List
from importlib.util import spec_from_file_location, module_from_spec

from jinja2 import Template
from jinja2.exceptions import TemplateSyntaxError
from embryo import Project
from appyratus.types import Yaml

from .exceptions import EmbryoNotFound, TemplateLoadFailed
from .environment import build_env
from .embryo import Embryo
from .constants import EMBRYO_FILE_NAMES, EMBRYO_PATH_ENV_VAR_NAME


class EmbryoGenerator(object):
    """
    Evaluates and generates an embryo project.
    """

    @classmethod
    def from_args(cls, args):
        """
        Generate en embryo using command line (CLI) arguments as the initial
        context dict (before the context.yml/json file is merged in, etc.)
        """
        cli_kwargs = {  # command-line (CLI) kwargs
            k: getattr(args, k)
            for k in dir(args) if not k.startswith('_')
        }
        return cls().create(
            name=cli_kwargs['embryo'],
            dest=cli_kwargs['dest'],
            context=cli_kwargs)

    @staticmethod
    def log(message):
        """
        Convenience logging method.
        """
        # TODO: Use python logging.
        print('>>> ' + message)

    def __init__(self):
        """
        Build the embryo search path, which consists of directories containing
        embryos. These locations are searched in the order in which they are
        defined when loading an embryo.
        """
        # the jinja2 env is used in rendering filepath template strings
        # as well as the templatized tree.yml file.
        self.jinja_env = build_env()

        # build the embryo search path
        self.embryo_search_path = [os.getcwd()]
        if EMBRYO_PATH_ENV_VAR_NAME in os.environ:
            raw_path_str = os.environ[EMBRYO_PATH_ENV_VAR_NAME]
            self.embryo_search_path.extend(raw_path_str.split(':'))

    def create(
        self,
        name: str,
        dest: str = None,
        context: Dict = None,
    ) -> List[Project]:
        """
        Generate an embryo, along with any embryos nested therein. Returns a
        list of Project objects. The first instance is the embryo being
        generated, and the rest are the nested ones.
        """

        dest = dest or './'

        # get an absolute filepath to the embryo directory
        path = self._resolve_embryo_path(name)

        # load context and other objects that are not templatized.
        embryo = self._load_embryo(path)
        context = self._load_context(path, dest, context)

        # run custom pre-create logic before project is built.
        if embryo:
            self.log('Running Embryo.pre_create hook...')
            context = embryo.apply_pre_create(context)

        # load the templates, including the tree yaml.
        templates = self._load_templates(path, context)
        tree = self._load_tree(path, context)

        # finally, build this project first, followed by any nested embryos. We
        # run the post-create logic after all nested projects have been built
        # so that we have known and fixed state at that point
        projects = []

        projects.append(
            self._build_project(embryo, path, context, dest, tree, templates)
        )
        projects.extend(
            self._build_nested_projects(embryo, path, context, projects[0])
        )

        # run any custom post-create logic that follows project creation
        if embryo:
            self.log('Running Embryo.post_create hook...')
            embryo.apply_post_create(projects[0], context)

        return projects

    def _resolve_embryo_path(self, name: str) -> str:
        """
        Return the filepath for the embryo with the given name.
        """
        name = name.rstrip('/')
        if inspect.ismodule(name):
            # path to the provided python module
            return name.__path__._path[0]
        elif name[0] == '/':
            # absolute path to embryo dir
            return name
        else:
            for path in self.embryo_search_path:
                path = '{}/{}'.format(path.rstrip('/'), name)
                if os.path.exists(path):
                    return path

        raise EmbryoNotFound(name)

    def _load_templates(self, path: str, context: Dict):
        """
        Read all template file. Each template string is stored in a dict, keyed
        by the relative path at which it exists, relative to the templates root
        directory. The file paths themselves are templatized and are therefore
        rendered as well in this procedure.
        """
        templates_path = self._build_filepath(path, 'templates')
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
                    self.log('Bad file path template: "{}"'.format(fpath))
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

    def _load_tree(self, path: str, context: Dict) -> Dict:
        """
        Read and deserialized the file system tree yaml file as well as render
        it, as it is a templatized file.
        """
        fpath = self._build_filepath(path, 'tree')
        with open(fpath) as tree_file:
            tree_yml_tpl = tree_file.read()
            tree_yml = self.jinja_env.from_string(tree_yml_tpl).render(context)
            return yaml.load(tree_yml)

    def _load_context(
        self,
        path: str,
        dest: str,
        cli_kwargs: Dict = None
    ) -> Dict:
        """
        Context can come from three places and is merged into a computed dict
        in the following order:

            1. Data in the embryo's static context.json/yml file.
            2. Variables provided on the commandline interface, like --foo 1.
            3. Data provided from a file, named in the --context CLI arg.
            4. Load data stored in the dest directory under the .embryo dir.
        """
        fpath = self._build_filepath(path, 'context')
        context = Yaml.from_file(fpath) or {}

        # if a --context PATH_TO_JSON_FILE was provided on the CLI then try to
        # load that file and merge it into the existing context dict.
        cli_context_value = cli_kwargs.pop('context', None)
        if cli_context_value:
            if cli_context_value.endswith('.json'):
                with open(context_filepath) as context_file:
                    cli_context = json.load(context_file)
            elif cli_context_value.endswith('.yml'):
                cli_context = Yaml.from_file(context_filepath)
            else:
                # assume it's a JSON object string
                cli_context = json.loads(cli_context_value)

            context.update(cli_context)

        # we collect params used by Embryo creation into a separate "embryo"
        # subobject and add it to the context dict with setdefault so as not to
        # overwrite any user defined variable by the same name, "embryo":
        context.setdefault('embryo', {
            'name': cli_kwargs.pop('embryo'),
            'path': path,
            'destination': os.path.abspath(cli_kwargs.pop('dest')),
            'action': cli_kwargs.pop('action'),
        })

        # Note that the remaining CLI kwargs should be custom context variables,
        # not Embryo creation parameters. We add these vars here.
        context.update(cli_kwargs)

        return context

    def _load_embryo(self, path):
        """
        The actual embryo is a Python object that contains various functions
        related to the generation of the project, like pre- and post-create
        hooks. This method loads, instantiates and returns it.
        """
        abs_filepath = self._build_filepath(path, 'embryo')
        embryo = None

        if os.path.isfile(abs_filepath):
            # imprt the embryo.py module
            spec = spec_from_file_location('module', abs_filepath)
            module = module_from_spec(spec)
            spec.loader.exec_module(module)

            # create an instance of the first Embryo subclass found
            for _, klass in inspect.getmembers(module, inspect.isclass):
                if issubclass(klass, Embryo):
                    embryo = klass()
                    break

        return embryo

    def _build_project(
        self,
        embryo, 
        path,
        context,
        root,
        tree,
        templates,
    ) -> Project:
        """
        This takes all the prepared data structures and uses them to create a
        Project and build it. The build project is returned.
        """
        root = os.path.abspath(root or './')

        self.log('Creating embryo...')
        self.log('Embryo: {}'.format(path))
        self.log('Destination: {}'.format(root))

        project = Project(root=root, tree=tree, templates=templates)
        project.build(embryo, context)

        self.log('Context: {}'.format(
            json.dumps(context, indent=2, sort_keys=True)
        ))

        return project

    def _build_nested_projects(
        self,
        embryo,
        path,
        context,
        project
    ) -> List[Project]:
        """
        All nested embryos declared in the embryo tree are built here,
        recursively. The list of Projects is returned.
        """
        nested_projects = []

        for item in project.nested_embryos:
            # extract the nested context sub-dict to pass into the nested
            # project as its own context, if specified.
            ctx_path = item.get('context_path')
            ctx_obj = self._get_nested_dict(ctx_path, context)

            nested_projects.append(
                self.create(
                    name=item['embryo_name'],
                    dest=item['dir_path'],
                    context=ctx_obj,
                )
            )

        return nested_projects

    @staticmethod
    def _build_filepath(path: str, key: str) -> str:
        """
        This builds an absolute filepath to a recognized file in a well-formed
        embryo. See EMBRYO_FILE_NAMES.
        """
        assert key in EMBRYO_FILE_NAMES
        return os.path.join(path, EMBRYO_FILE_NAMES[key])

    @staticmethod
    def _get_nested_dict(dotted_path, root_dict):
        """
        Return a nested dictionary, located by its dotted path. If the dict is
        {a: {b: {c: 1}}} and the path is a.b, then {c: 1} will be returned.
        """
        d = root_dict
        for k in dotted_path.split('.'):
            d = d[k]
        return d
