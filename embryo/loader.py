import os
import inspect
import json

from typing import Dict, List
from importlib.util import spec_from_file_location, module_from_spec

from embryo import Project

from .exceptions import EmbryoNotFound
from .embryo import Embryo
from .constants import EMBRYO_FILE_NAMES, EMBRYO_PATH_ENV_VAR_NAME


class Loader(object):
    """
    The duty of the `Loader` is to find and load the `Embryo` object
    from the filesystem and send it into a `Project` to be built. The `Embryo`
    object contains the instructions, as it were, for building the embryo in
    the filesystem; while the `Project` is responsible for the building.
    """

    def load(
        self,
        name: str,
        destination: str = None,
        context: Dict = None,
    ) -> List[Project]:
        """
        Generate an embryo, along with any embryos nested therein. Returns a
        list of Project objects. The first instance is the embryo being
        generated, and the rest are the nested ones.
        """
        # get an absolute filepath to the embryo directory
        embryo_path = self._resolve_embryo_path(name)
        embryo = self._instantiate_embryo(embryo_path, destination, context)

        # run custom pre-create logic before project is built.
        embryo.apply_pre_create()

        # finally, build this project first, followed by any nested embryos. We
        # run the post-create logic after all nested projects have been built
        # so that we have known and fixed state at that point
        projects = [self._build_project(embryo)]
        projects.extend(self._build_nested_projects(embryo, projects[0]))

        # run any custom post-create logic that follows project creation
        embryo.apply_post_create(projects[0])

        return projects

    def __init__(self):
        self._embryo_search_path = self._build_embryo_path()

    def _build_embryo_path(self):
        """
        Build an ordered list of all directories to search when loading an
        embryo from the filesystem.
        """
        search_path = [os.getcwd()]
        if EMBRYO_PATH_ENV_VAR_NAME in os.environ:
            raw_path_str = os.environ[EMBRYO_PATH_ENV_VAR_NAME]
            search_path.extend(raw_path_str.split(':'))
        return search_path

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
            for path in self._embryo_search_path:
                path = '{}/{}'.format(path.rstrip('/'), name)
                if os.path.exists(path):
                    return path

        raise EmbryoNotFound(name)

    def _instantiate_embryo(self, path, destination, context):
        """
        The actual embryo is a Python object that contains various functions
        related to the generation of the project, like pre- and post-create
        hooks. This method loads and returns an instance.
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
                if issubclass(klass, Embryo) and klass is not Embryo:
                    embryo_class = klass
                    embryo = klass(path)
                    break

        if embryo is None:
            # In this case, just use the base class
            embryo = Embryo(path)

        # This computes the final context object and loads the templates
        # and filesystem tree....
        embryo.load(destination, context)

        return embryo

    def _build_project(self, embryo) -> Project:
        """
        This takes all the prepared data structures and uses them to create a
        Project and build it. The build project is returned.
        """
        self._log('Creating embryo...')
        self._log('Embryo: {}'.format(embryo.path))
        self._log('Destination: {}'.format(embryo.destination))

        project = Project(embryo)
        project.build()

        self._log('Context: {}'.format(
            json.dumps(embryo.context, indent=2, sort_keys=True)
        ))

        return project

    def _build_nested_projects(self, embryo, project) -> List[Project]:
        """
        All nested embryos declared in the embryo tree are built here,
        recursively. The list of Projects is returned.
        """
        nested_projects = []

        for item in project.nested_embryos:
            # extract the nested context sub-dict to pass into the nested
            # project as its own context, if specified.
            ctx_path = item.get('context_path')
            ctx_obj = self._get_nested_dict(ctx_path, embryo.context)

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

    @staticmethod
    def _log(message):
        """
        Convenience logging method.
        """
        # TODO: Use python logging.
        print('>>> ' + message)

