import os
from collections import defaultdict
from copy import deepcopy
from typing import (
    Dict,
    List,
    Text,
)

from appyratus.files import Json

from .utils import (
    build_embryo_search_path,
    import_embryo_class,
    resolve_embryo_path,
    say,
    shout,
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
        To be run *after* the renderer is built. This loads all context.json
        files found in the filesystem, relative to a root directory. It imports
        and instantiates the Python Embryo objects corresponding to the persist
        context entries. This is called by the embryo `apply_on_create` method.
        """

        root = embryo.destination

        for path, subpaths, fnames in os.walk(root):
            json_fpath = os.path.join(path, '.embryo/context.json')
            # if os.path.isfile(json_fpath):
            # TODO: re-enable logging when logger interface is updated
            #     say('Loading embryos from {path}...', path=json_fpath)
            embryo_name2context_list = self._load_context_json(json_fpath)
            for embryo_name, context_list in embryo_name2context_list.items():
                count = len(context_list)
                say(
                    'loading embryo: "{name}" ({count}x)...',
                    name=embryo_name,
                    count=count
                )
                for context in context_list:
                    embryo = self._load_embryo(context)
                    if embryo is None:
                        shout(
                            f'failed to load embryo from .embryo/'
                            f'context.json: {context}'
                        )
                        continue

                    # the `path_key` is is the relative path to the current
                    # `path` directory, prepended with a '/'
                    path_key = '/' + path[len(root):]

                    # this is the key for the named_path lookup table:
                    named_path = (embryo_name, path_key)

                    # add the embryo to internal lookup tables:
                    self._named_path2embryos[named_path].append(embryo)
                    self._name2embryos[embryo_name].append(embryo)
                    self._path2embryos[path_key].append(embryo)

    def find(self, name: Text = None, path: Text = None) -> List['Embryo']:
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

    def persist(self, embryo: 'Embryo') -> None:
        """
        Initialize the .embryo directory if it doesn't exist and append the
        embryo's context dict to the context.json file.
        """
        dot_embryo_path = self._resolve_dot_dir(embryo)
        context_json_path = os.path.join(dot_embryo_path, 'context.json')
        embryo_name_2_contexts = {}

        # create or load the .embryo/ dir in the "root" dir
        if not os.path.isdir(dot_embryo_path):
            say('creating .embryo directory: {path}', path=dot_embryo_path)
            os.mkdir(dot_embryo_path)

        # load the JSON file
        if os.path.isfile(context_json_path):
            # read in the current data structure
            embryo_name_2_contexts = Json.read(context_json_path)

        # adding to the JSON file data by adding it to the list of other
        # embryos generated here of the same name.
        schema = embryo.context_schema()
        if schema:
            context, errors = schema.process(embryo.context, strict=True)

        # clean up embryo context, as we want to remove some information- like
        # the embryo destination, which can vary from user to user
        clean_embryo_context = deepcopy(embryo.loaded_context)
        del clean_embryo_context['embryo']['destination']

        if embryo.name not in embryo_name_2_contexts:
            embryo_name_2_contexts[embryo.name] = [clean_embryo_context]
        else:
            embryo_name_2_contexts[embryo.name].append(clean_embryo_context)

        # write the appended data back to the JSON file
        say('saving context to .embryo/context.json file')
        Json.write(
            context_json_path,
            Json.load(Json.dump(embryo_name_2_contexts)),
            indent=2,
            sort_keys=True
        )

    def _load_context_json(self, context_json_fpath: Text) -> Dict:
        """
        Read in a context.json file to a dict.
        """
        loaded_json_obj = {}

        if os.path.isfile(context_json_fpath):
            loaded_json_obj = Json.read(context_json_fpath)

        return loaded_json_obj

    def _load_embryo(self, context) -> 'Embryo':
        """
        Import and instantiate an Embryo object using a context dict loaded
        from a context.json file.
        """
        name = context['embryo']['name']

        try:
            embryo_path = resolve_embryo_path(
                self._embryo_search_path, name
            )
        except Exception as exc:
            shout(exc)
            return None

        embryo_class = import_embryo_class(embryo_path)
        if embryo_class is not None:
            embryo = embryo_class(embryo_path, context)
            return embryo
        else:
            return None

    def _resolve_dot_dir(self, embryo):

        def is_dot_dir(path):
            return path.endswith('.embryo')

        def analyze_node(node, parent_path: Text = ''):
            if node is None:
                return None
            if isinstance(node, str):
                path = os.path.join(parent_path, node)
                if is_dot_dir(path):
                    return os.path.join(embryo.destination, path)
            else:
                node_name = list(node.keys())[0]
                parent_path = os.path.join(parent_path, node_name)
                for children in node.values():
                    if not children:
                        continue
                    for child_node in children:
                        dot_dir = analyze_node(child_node, parent_path)
                        if dot_dir:
                            return dot_dir
            return None

        if embryo.tree:
            for node in embryo.tree:
                dot_dir = analyze_node(node)
                if dot_dir:
                    return dot_dir

        return os.path.join(embryo.destination, '.embryo')
