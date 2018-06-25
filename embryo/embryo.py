import os
import yaml

from typing import Dict

from jinja2 import Template
from jinja2.exceptions import TemplateSyntaxError

from appyratus.validation import Schema
from appyratus.validation import fields
from appyratus.types import Yaml

from .project import Project
from .environment import build_env
from .exceptions import TemplateLoadFailed
from .constants import EMBRYO_FILE_NAMES
from .utils import say, shout, build_embryo_filepath


class ContextSchema(Schema):
    """
    Returns an instance of a Schema class, which is applied to the context
    dict, using schema.load(context). A return value of None skips this
    process, i.e. it is optional.
    """
    fs = fields.Dict()
    embryo = fields.Object({
        'timestamp': fields.DateTime(),
        'name': fields.Str(),
        'action': fields.Str(),
        'path': fields.Str(),
        'destination': fields.Str(),
    })


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

    def __repr__(self):
        return '<{class_name}({embryo_path})>'.format(
            class_name=self.__class__.__name__,
            embryo_path=self._path,
        )

    def load(self, context, from_fs=False):
        self.context = self._load_context(context, from_fs)
        self.tree = self._load_tree(self.context)
        self.templates = self._load_templates(context)

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

    def on_create(self, project: Project, fs: Dict) -> None:
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
        say('Running pre-create method...')

        # load/validate context as prepared by the Loader and Project
        # during the buld process.
        schema = self.context_schema()
        if schema:
            self.context = schema.load(self.context, strict=True).data

        self.pre_create()

        # we re-load the context because it is possible that it has been
        # modified in-place by pre_create.
        if schema:
            # TODO: all we want to do is re-validate here, not reload
            self.context = schema.load(self.context, strict=True).data

    def apply_on_create(self, project: Project, fs: Dict) -> None:
        say('Running on-create method...')
        self.on_create(project, fs)

        # we re-load the context because it is possible that it has been
        # modified in-place by pre_create.
        schema = self.context_schema()
        if schema:
            # TODO: all we want to do is re-validate, not reload
            self.context = schema.load(self.context, strict=True).data

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
        if not from_fs:
            context.setdefault('embryo', {
                'name': cli_kwargs.pop('embryo'),
                'path': path,
                'destination': os.path.abspath(cli_kwargs.pop('dest')),
                'action': cli_kwargs.pop('action'),
            })

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
                    shout('Could not render template '
                          'for file path string: {p}', p=fpath)
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
