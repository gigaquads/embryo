import os

import ujson

from typing import Dict, List
from collections import defaultdict

from .utils import (
    say, shout, resolve_embryo_path,
    import_embryo_class, build_embryo_search_path,
)


class DotFileManager(object):
    """
    `DotFileManager` handles the loading of contents stored under the .embryo
    directories contained within the filesystem tree defined by an embryo. It
    provides a high-level interface for searching historical Embryo objects
    whose context data was discovered in .embryo/context.json files.
    """
    def __init__(self):
        self._embryo_search_path = build_embryo_search_path()
        self._named_path2embryos = defaultdict(list)
        self._name2embryos = defaultdict(list)
        self._path2embryos = defaultdict(list)

    def load(self, embryo: 'Embryo') -> None:
        """
        To be run *after* the project is built. This loads all context.json
        files found in the filesystem, relative to a root directory. It imports
        and instantiates the Python Embryo objects corresponding to the persist
        context entries. This is called by the embryo `apply_on_create` method.
        """
        root = embryo.destination

        for path, subpaths, fnames in os.walk(root):
            json_fpath = os.path.join(path, '.embryo/context.json')
            if os.path.isfile(json_fpath):
                say('Reading {path}...', path=json_fpath)
            embryo_name2context_list = self._load_context_json(json_fpath)
            for embryo_name, context_list in embryo_name2context_list.items():
                count = len(context_list)
                say('Importing embryo: "{name}" - {count}x...',
                    name=embryo_name,
                    count=count
                )
                for context in context_list:
                    embryo = self._load_embryo(context)

                    # the `path_key` is is the relative path to the current
                    # `path` directory, prepended with a '/'
                    path_key = '/' + path[len(root):]

                    # this is the key for the named_path lookup table:
                    named_path = (embryo_name, path_key)

                    # add the embryo to internal lookup tables:
                    self._named_path2embryos[named_path].append(embryo)
                    self._name2embryos[embryo_name].append(embryo)
                    self._path2embryos[path_key].append(embryo)

    def find(self, name: str = None, path: str = None) -> List['Embryo']:
        """
        Return a list of Embryo objects discovered in the filesystem tree
        relative to the root directory passed into the `load` method. Name or
        path or both can be specified. When both are specified, we return the
        Embryos with the given name within the given directory path.
        """
        if name and (not path):
            return self._name2embryos[name]
        elif (not name) and path:
            return self._path2embryos[path]
        elif name and path:
            return self._named_path2embryos[name, path]
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

    def _load_embryo(self, context) -> 'Embryo':
        """
        Import and instantiate an Embryo object using a context dict loaded
        from a context.json file.
        """
        name = context['embryo']['name']
        embryo_path = resolve_embryo_path(self._embryo_search_path, name)
        embryo_class = import_embryo_class(embryo_path)
        embryo = embryo_class(embryo_path, context)
        return embryo
