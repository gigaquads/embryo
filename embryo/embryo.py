import os
import json
import inspect

from typing import Dict, List
from collections import defaultdict

from jinja2.exceptions import TemplateSyntaxError

from appyratus.schema import Schema, fields
from appyratus.files import File, Yaml

from .renderer import Renderer
from .environment import build_env
from .exceptions import TemplateLoadFailed
from .constants import (
    EMBRYO_FILE_NAMES,
    RE_RENDERING_EMBRYO,
    NESTED_EMBRYO_KEY,
)
from .relationship import Relationship, RelationshipManager
from .filesystem import (
    CssAdapter,
    FileTypeAdapter,
    HtmlAdapter,
    IniAdapter,
    JsonAdapter,
    MarkdownAdapter,
    PythonAdapter,
    TextAdapter,
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
    get_nested_dict,
)


class ContextSchema(Schema):
    """
    Returns an instance of a Schema class, which is applied to the context
    dict, using schema.process(context). A return value of None skips this
    process, i.e. it is optional.
    """
    embryo = fields.Nested(
        {
            'timestamp': fields.DateTime(),
            'name': fields.String(),
            'action': fields.String(),
            'path': fields.String(),
            'destination': fields.String(),
        }
    )


class Embryo(object):
    """
    Embryo objects serve as an interface to performing various actions within
    the context of running the Incubator.
    """

    Schema = ContextSchema

    def __init__(self, path: str, context: Dict):
        self.path = path

        self.jinja_env = build_env()
        self.context = self._build_context(context)
        self.schema = self.context_schema()
        self.renderer = Renderer()
        self.dot = DotFileManager()
        self.fs = FileManager()

        self.related = {}
        self.nested = defaultdict(list)
        self.loaded_context = None
        self.dumped_context = None
        self.templates = None
        self.tree = None

    def __repr__(self):
        return '<{class_name}({embryo_path})>'.format(
            class_name=self.__class__.__name__,
            embryo_path=self.path,
        )

    @property
    def adapters(self) -> List[FileTypeAdapter]:
        return [
            PythonAdapter(),
            CssAdapter(),
            JsonAdapter(indent=2, sort_keys=True),
            HtmlAdapter(),
            IniAdapter(),
            MarkdownAdapter(),
            TextAdapter(),
            YamlAdapter(multi=True),
        ]

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
        dict, using schema.process(context). A return value of None skips this
        process, i.e. it is optional.
        """
        return ContextSchema()

    def pre_create(self, context) -> None:
        """
        Perform any side-effects or preprocessing before the embryo Renderer and
        related objects are created. if a context_schema exists, the `context`
        argument is the marshaled result of calling `schema.process(context)`.
        This method should be overridden.
        """

    def on_create(self, context) -> None:
        """
        Here, we assume that the context data is finished being prepared for
        dispatch to the template renderer. We can access the fully-loaded tree
        and file data provided by the FileManager
        """

    def post_create(self, context) -> None:
        """
        Post_create is called upon the successful creation of the Renderer
        object. Any side-effects following the creation of the embryo in the
        filesystem can be performed here. This method should be overridden.
        """

    def persist(self):
        """
        Write this embryo's context to its .embryo/context.json file.
        """
        self.dot.persist(self)

    def hatch(self) -> None:
        """
        This method loads pre-rendered templates. This includes file templates
        in the templates/ dir as well as the tree.yml file, which is also a
        template.
        """
        say('Stimulating embryonic growth sequence...')
        say('Hatching Embryo: "{name}"', name=self.name)
        say('Embryo Location: {path}', path=self.path)
        say('Destination: {dest}', dest=self.destination)

        # Load all Embryo objects discovered in
        # context.json files present in the filesystem,
        # relative to this embryo's destination directory.
        self.dot.load(self)

        # Generates a dict that maps relationship name
        # to Embryo object, found by the dot file manager,
        # using Relationship ctor arguments.
        self.related = RelationshipManager().load(self)

        say('Running pre-create method...')
        self.pre_create(self.context)

        # Now there can be no more edits to self.context,
        # so we load the raw context dict and dump it into
        # the templates for rendering.
        self.loaded_context = self._load_context()
        self.dumped_context = self._dump_context()

        # Render the tree.yml template.
        self.tree = self._render_tree()

        # Load raw template strings into dict with absolute
        # file paths as keys.
        self.templates = self._load_templates()

        # Render the files declared in the tree.
        self.renderer.render(self)

        # Read files that already exist in filesystem using
        # available filetype adapters.
        self.fs.read(self)

        # Resolve and instantiate Embryo objects
        # "nested" in tree.yml.
        self._load_nested_embryos()

        say('Running on-create method...')
        self.on_create(self.dumped_context)

        # Write files loaded by FileManager back to disk,
        # using available filetype adapters.
        self.fs.write()

        # Call hatch() on all nested embryos in
        # depth-first traversal.
        self._hatch_nested_embryos()

        say('Running post-create method...')
        self.post_create(self.dumped_context)

    def _load_nested_embryos(self):
        search_path = build_embryo_search_path()

        def load_recursive(nodes, path):
            if not nodes:
                return
            for obj in nodes:
                if isinstance(obj, dict):
                    key = list(obj.keys())[0]
                    if key == NESTED_EMBRYO_KEY:
                        match = RE_RENDERING_EMBRYO.match(obj[key])
                        embryo_name, context_path = match.groups()
                        dest_dir = os.path.abspath(path)
                        load_embryo(embryo_name, context_path, dest_dir)
                    else:
                        child_nodes = obj[key]
                        load_recursive(child_nodes, os.path.join(path, key))

        def load_embryo(embryo_name, context_path, dest_dir):
            assert self.loaded_context
            say('Hatching nested embryo: {name}...', name=embryo_name)
            found_context = get_nested_dict(self.loaded_context, context_path)
            if found_context:
                context = found_context.copy()
            else:
                context = {}
            context['embryo'] = self.context['embryo']
            embryo_path = resolve_embryo_path(search_path, embryo_name)
            embryo_factory = import_embryo_class(embryo_path)
            embryo = embryo_factory(embryo_path, context)
            self.nested[dest_dir].append(embryo)

        # this loads the embryos into self.nested
        load_recursive(self.tree, '')

    def _hatch_nested_embryos(self):
        from embryo.incubator import Incubator
        for embryo_list in self.nested.values():
            for embryo in embryo_list:
                incubator = Incubator.from_embryo(embryo)
                incubator.hatch()

    def _load_context(self):
        assert self.context is not None
        retval = {}
        schema = self.context_schema()
        if schema:
            result, errors = schema.process(self.context)
            if errors:
                shout(
                    'Failed to load context: {errors}',
                    errors=json.dumps(errors, indent=2, sort_keys=True)
                )
                exit(-1)
            retval.update(result)
        retval['embryo'] = self.context['embryo']
        return retval

    def _dump_context(self):
        """
        Dump schema to context and update with related attributes
        """
        assert self.loaded_context is not None
        dumped_context, errors = self.schema.process(self.loaded_context)
        dumped_context.update(self.related)
        return dumped_context

    def _build_context(self, context: Dict=None) -> Dict:
        """
        Context can come from three places and is merged into a computed dict
        in the following order:

            1. Data in the embryo's static context.json/yml file.
            2. Variables provided on the commandline interface, like --foo 1.
            3. Data provided from a file, named in the --context arg.
        """
        path = self.path
        fpath = build_embryo_filepath(path, 'context')

        dynamic_context = context
        static_context = Yaml.read(fpath) or {}

        merged_context = {}
        merged_context.update(static_context)
        merged_context.update(dynamic_context)

        return merged_context

    def _load_templates(self):
        """
        Read all template file. Each template string is stored in a dict, keyed
        by the relative path at which it exists, relative to the templates root
        directory. The file paths themselves are templatized and are therefore
        rendered as well in this procedure.
        """
        assert self.dumped_context is not None

        say('Loading templates...')

        context = self.dumped_context
        templates_path = build_embryo_filepath(self.path, 'templates')
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

    def _render_tree(self) -> Dict:
        """
        Read and deserialized the file system tree yaml file as well as render
        it, as it is a templatized file.
        """
        assert self.dumped_context is not None

        say('Rendering tree.yml...')

        context = self.dumped_context.copy()
        context.update(self.related)
        fpath = build_embryo_filepath(self.path, 'tree')
        
        tree_yml_tpl = File.read(fpath)
        if tree_yml_tpl is None:
            shout('No tree in {}'.format(fpath))
            return 
        tree_yml = self.jinja_env.from_string(tree_yml_tpl).render(context)
        tree = Yaml.load(tree_yml)
        return tree
