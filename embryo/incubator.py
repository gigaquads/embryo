import os
import inspect
import json

from typing import Dict, List

from appyratus.json import JsonEncoder
from appyratus.time import utc_now

from embryo import Renderer

from .exceptions import EmbryoNotFound
from .embryo import Embryo
from .constants import EMBRYO_FILE_NAMES, EMBRYO_PATH_ENV_VAR_NAME
from .utils import (
    say, shout, build_embryo_filepath, get_nested_dict,
    import_embryo_class, resolve_embryo_path, build_embryo_search_path,
)


class Incubator(object):
    """
    The duty of the `Incubator` is to find and load the `Embryo` object
    from the filesystem and send it into a `Renderer` to be built. The `Embryo`
    object contains the instructions, as it were, for building the embryo in
    the filesystem; while the `Renderer` is responsible for the building.
    """

    @classmethod
    def from_embryo(cls, embryo: 'Embyro'):
        incubator = cls(embryo_name=None, destination=None)
        incubator._embryo = embryo
        incubator._embryo_path = embryo.path
        incubator._embryo_class = embryo.__class__
        return incubator

    def __init__(
        self,
        embryo_name: str,
        destination: str,
        context: Dict = None,
        embryo: 'Embryo' = None,
    ):
        """
        Generate an embryo, along with any embryos nested therein. Returns a
        list of Renderer objects. The first instance is the embryo being
        generated, and the rest are the nested ones.

        # Args
        - `embryo_name`: The name of the embryo.
        - `destination`: Directory to hatch embryo into
        - `context`: Context data to merge into other sources.
        """
        self._embryo_search_path = build_embryo_search_path()
        self._json_encoder = JsonEncoder()
        self._embryo_class = None
        self._embryo_path = None
        self._embryo = None

        if embryo_name is None:
            # this should mean we're coming from the
            # from_embryo factory method
            return

        # ------
        # Add Embryo metadata to context
        context.update({
            'embryo': {
                'name': embryo_name,
                'destination': os.path.abspath(os.path.expanduser(destination)),
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
    
    @property
    def embryo(self):
        return self._embryo

    def hatch(self) -> None:
        """
        This takes all the prepared data structures and uses them to create a
        Renderer and build it. The build renderer is returned.
        """
        self.embryo.hatch()
