import os
import inspect
import json

from typing import Dict, List

from appyratus.json import JsonEncoder
from appyratus.time import utc_now

from embryo import Project

from .exceptions import EmbryoNotFound
from .embryo import Embryo
from .constants import EMBRYO_FILE_NAMES, EMBRYO_PATH_ENV_VAR_NAME
from .utils import (
    say, shout, build_embryo_filepath, get_nested_dict,
    import_embryo_class, resolve_embryo_path, build_embryo_search_path,
)

# TODO: Rename to Incubator
class Incubator(object):
    """
    The duty of the `Incubator` is to find and load the `Embryo` object
    from the filesystem and send it into a `Project` to be built. The `Embryo`
    object contains the instructions, as it were, for building the embryo in
    the filesystem; while the `Project` is responsible for the building.
    """

    def __init__(
        self,
        embryo_name: str,
        destination: str,
        context: Dict = None,
    ):
        """
        Generate an embryo, along with any embryos nested therein. Returns a
        list of Project objects. The first instance is the embryo being
        generated, and the rest are the nested ones.

        # Args
        - `embryo_name`: The name of the embryo.
        - `destination`: Directory to hatch embryo into
        - `context`: Context data to merge into other sources.
        """
        self._embryo_search_path = build_embryo_search_path()
        self._json_encoder = JsonEncoder()

        # Add Embryo metadata to context
        context.update({
            'embryo': {
                'name': embryo_name,
                'destination': os.path.abspath(destination),
                'timestamp': utc_now(),
                'action': 'hatch',
            }
        })

        # Get the absolute path to the embryo directory
        self._embryo_path = resolve_embryo_path(
            self._embryo_search_path, embryo_name
        )

        say('Searching for embryos in...\n\n    - {paths}\n',
            paths='\n    - '.join(self._embryo_search_path)
        )

        # Import the Embryo class from embryo dir and instantaite it.
        self._embryo_class = import_embryo_class(self._embryo_path)
        self._embryo = self._embryo_class(self._embryo_path, context)

    def hatch(self) -> List[Project]:
        """

        $ Returns
        A list of Project objects, where the first element is the embryo being
        loaded, followed by nested projects in breadth-first order.
        """
        # run custom pre-create logic before project is built.
        self._embryo.apply_pre_create()

        # finally, build this project first, followed by any nested embryos. We
        # run the post-create logic after all nested projects have been built
        # so that we have known and fixed state at that point
        projects = self._build_project()

        # run any custom post-create logic that follows project creation
        self._embryo.apply_post_create(projects[0])

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
            for path in self._embryo_search_path:
                path = '{}/{}'.format(path.rstrip('/'), name)
                if os.path.exists(path):
                    return path

        raise EmbryoNotFound(name)

    def _build_project(self) -> Project:
        """
        This takes all the prepared data structures and uses them to create a
        Project and build it. The build project is returned.
        """
        parent_project = Project(self._embryo)
        parent_project.build()

        child_projects = self._build_nested(parent_project)

        projects = [parent_project]
        projects.extend(child_projects)

        return projects

    def _build_nested(self, project) -> List[Project]:
        """
        All nested embryos declared in the embryo tree are built here,
        recursively. The list of Projects is returned.
        """
        nested_projects = []

        for item in project.nested_embryos:
            # extract the nested context sub-dict to pass into the nested
            # project as its own context, if specified.
            ctx_path = item.get('context_path')
            ctx_obj = get_nested_dict(self._embryo.context, ctx_path)

            say('Hatching nested embryo: {name}...', name=item['embryo_name'])

            incubator = Incubator(
                embryo_name=item['embryo_name'],
                destination=item['dir_path'],
                context=ctx_obj,
            )

            nested_projects.extend(incubator.hatch())

        return nested_projects
