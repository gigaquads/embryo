import os
from collections import defaultdict
from copy import deepcopy
from typing import (
    Dict,
    List,
    Text,
)

from appyratus.files import Json, Yaml
from appyratus.utils import PathUtils as Path
from embryo.constants import EMBRYO_FILE_NAMES

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
    whose context data was discovered in embryo context files.
    """

    def __init__(self):
        self._embryo_search_path = build_embryo_search_path()
        self._named_path2embryos = defaultdict(list)
        self._name2embryos = defaultdict(list)
        self._path2embryos = defaultdict(list)

    def load(self, embryo: 'Embryo') -> None:
        """
        To be run *after* the renderer is built. This loads all embryo context
        files found in the filesystem, relative to a root directory. It imports
        and instantiates the Python Embryo objects corresponding to the persist
        context entries. This is called by the embryo `apply_on_create` method.
        """

        root = embryo.destination

        for path, subpaths, fnames in os.walk(root):
            context_fpath = self._build_metadir(path)
            context_fpath, context, context_ext, context_type = self.get_context(
                context_fpath
            )
            if os.path.isfile(context_fpath):
                say('Loading embryos from {path}...', path=context_fpath)
            embryo_name2context_list = context
            for embryo_name, context_list in embryo_name2context_list.items():
                count = len(context_list)
                say(
                    'Loading embryo: "{name}" ({count}x)...',
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
        embryo's context dict to the embryo context file.
        """
        context_path = self._resolve_dot_dir(embryo)
        context_ext = Path.get_extension(context_path)
        context_type = None
        metadata_path = Path.get_dir_path(context_path)
        embryo_name_2_contexts = {}
        context_files = []

        # create or load the metadata dir in the "root" dir
        if not os.path.isdir(metadata_path):
            say('Creating metadata directory: {path}', path=metadata_path)
            Path.create(metadata_path)

        context_path, embryo_name_2_contexts, context_ext, context_type = self.get_context(
            context_path
        )

        # adding to the JSON file data by adding it to the list of other
        # embryos generated here of the same name.
        schema = embryo.context_schema()
        if schema:
            context, errors = schema.process(embryo.context, strict=True)

        # clean up embryo context, as we want to remove some information- like
        # the embryo destination, which can vary from user to user
        clean_embryo_context = deepcopy(embryo.loaded_context)
        del clean_embryo_context['embryo']['destination']

        # add the embryo to the context
        if embryo.name not in embryo_name_2_contexts:
            embryo_name_2_contexts[embryo.name] = [clean_embryo_context]
        else:
            embryo_name_2_contexts[embryo.name].append(clean_embryo_context)

        # write the appended data back to the JSON file
        say('Saving context to {path}', path=context_path)
        contents = Json.load(Json.dump(embryo_name_2_contexts))
        context_type.write(context_path, contents)

    @classmethod
    def get_context(cls, context_path: Text):
        """
        # Get Context 
        Get context of the provided context path.  If that path does not exist,
        then known context file extensions will be tried.  And if those cannot
        be found then it will rely on the system default provided in constants
        
        Known file types include: Yaml, Json
        """
        if not context_path:
            context_path = cls._build_metadir()
        context_ext = Path.get_extension(context_path)
        ext_types = {Yaml, Json}
        context = None
        context_files = []
        for ext_type in ext_types:
            exts = ext_type.extensions()
            for ext in exts:
                new_path = Path.replace_extension(context_path, ext)
                ref = (new_path, ext, ext_type)
                if ext == context_ext:
                    context_files.insert(0, ref)
                else:
                    context_files.append(ref)

        # work through known context paths and read in the found data
        context_found = False
        for context_path, context_ext, context_type in context_files:
            if not os.path.isfile(context_path):
                continue
            context = context_type.read(context_path)
            if context:
                context_found = True
                break

        # if the context still cannot be found then use the first item in
        # context files list
        if not context_found:
            context_path, context_ext, context_type = context_files[0]
            context = {}
        return context_path, context, context_ext, context_type

    def _load_embryo(self, context) -> 'Embryo':
        """
        Import and instantiate an Embryo object using a context dict loaded
        from an embryo context file.
        """
        name = context['embryo']['name']
        embryo_path = resolve_embryo_path(self._embryo_search_path, name)
        embryo_class = import_embryo_class(embryo_path)
        embryo = embryo_class(embryo_path, context)
        return embryo

    @classmethod
    def _build_metadir(cls, path: Text = None):
        metadir = EMBRYO_FILE_NAMES['metadata-dir']
        context = EMBRYO_FILE_NAMES['context']
        parts = [metadir, context]
        if path:
            parts.insert(0, path)
        return Path.join(*parts)

    def _resolve_dot_dir(self, embryo):
        from embryo.constants import EMBRYO_FILE_NAMES

        def is_dot_dir(path):
            Path.get_dir_name(path) == EMBRYO_FILE_NAMES['metadata-dir']
            return '.embryo' in path

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

        res = self._build_metadir(embryo.destination)
        return res
