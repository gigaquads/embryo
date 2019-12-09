import os
import inspect

from typing import Dict, List
from importlib.util import spec_from_file_location, module_from_spec

from .exceptions import EmbryoNotFound
from .constants import (
    PROMPT_STYLES,
    EMBRYO_FILE_NAMES,
    EMBRYO_PATH_ENV_VAR_NAME,
)


def say(fstr, **format_vars) -> None:
    print(PROMPT_STYLES['say'] + ' ' + fstr.format(**format_vars))


def shout(fstr, **format_vars) -> None:
    print(PROMPT_STYLES['scream'] + ' ' + fstr.format(**format_vars))


def build_embryo_filepath(embryo_path: str, file_code: str) -> str:
    """
    This builds an absolute filepath to a recognized file in a well-formed
    embryo. See EMBRYO_FILE_NAMES.
    """
    assert file_code in EMBRYO_FILE_NAMES
    return os.path.join(embryo_path, EMBRYO_FILE_NAMES[file_code])


def build_embryo_search_path() -> List[str]:
    """
    Build an ordered list of all directories to search when loading an
    embryo from the filesystem.
    """
    search_path = [os.getcwd()]
    if EMBRYO_PATH_ENV_VAR_NAME in os.environ:
        raw_path_str = os.environ[EMBRYO_PATH_ENV_VAR_NAME]
        search_path.extend(raw_path_str.split(':'))

    visited = set()
    unique_search_path = []

    for k in search_path:
        if k not in visited:
            unique_search_path.append(k)
            visited.add(k)

    return unique_search_path


def resolve_embryo_path(search_path: List[str], name: str) -> str:
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
        for path in search_path:
            path = '{}/{}'.format(path.rstrip('/'), name)
            if os.path.exists(path):
                return path

    raise EmbryoNotFound(name)


def get_nested_dict(root: Dict, dotted_path: str = None) -> Dict:
    """
    Return a nested dictionary, located by its dotted path. If the dict is
    {a: {b: {c: 1}}} and the path is a.b, then {c: 1} will be returned.
    """
    d = root
    if not dotted_path:
        return root
    for k in dotted_path.split('.'):
        d = d[k]
    return d


def import_embryo_class(embryo_path: str) -> 'Embryo':
    """
    The actual embryo is a Python object that contains various functions
    related to the generation of the renderer, like pre- and post-create
    hooks. This method loads and returns an instance.
    """
    from embryo.embryo import Embryo

    # absolute file path to the embryo directory
    abs_filepath = build_embryo_filepath(embryo_path, 'embryo')

    embryo_class = None    # <- return value

    if os.path.isfile(abs_filepath):
        # imprt the embryo.py module
        spec = spec_from_file_location('module', abs_filepath)
        module = module_from_spec(spec)
        spec.loader.exec_module(module)

        # create an instance of the first Embryo subclass found
        for _, klass in inspect.getmembers(module, inspect.isclass):
            if issubclass(klass, Embryo) and klass is not Embryo:
                embryo_class = klass
                break

    return (embryo_class or Embryo)


def get_embryo_resource(embryo_name: str) -> tuple:
    """
    # Get Embryo Resource
    With the provided embryo name, resolve the embryo path as well as the class
    name to be instantiated by you.
    """
    embryo_search_path = build_embryo_search_path()
    # Get the absolute path to the embryo directory

    embryo_path = resolve_embryo_path(embryo_search_path, embryo_name)

    say(
        'Searching for embryos in...\n\n    - {paths}\n',
        paths='\n    - '.join(embryo_search_path)
    )

    # import the Embryo class from embryo dir and instantiate it.
    embryo_class = import_embryo_class(embryo_path)
    return (
        embryo_name,
        embryo_path,
        embryo_class,
    )
