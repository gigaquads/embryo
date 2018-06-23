import os

from typing import Dict

from .constants import (
    PROMPT_STYLES,
    EMBRYO_FILE_NAMES,
    EMBRYO_PATH_ENV_VAR_NAME,
)


def say(fstr, **format_vars):
    print(PROMPT_STYLES['say'] + ' ' + fstr.format(**format_vars))


def shout(fstr, **format_vars):
    print(PROMPT_STYLES['scream'] + ' ' + fstr.format(**format_vars))


def build_embryo_filepath(embryo_path: str, file_code: str) -> str:
    """
    This builds an absolute filepath to a recognized file in a well-formed
    embryo. See EMBRYO_FILE_NAMES.
    """
    assert file_code in EMBRYO_FILE_NAMES
    return os.path.join(embryo_path, EMBRYO_FILE_NAMES[file_code])


def get_nested_dict(root: Dict, dotted_path: str):
    """
    Return a nested dictionary, located by its dotted path. If the dict is
    {a: {b: {c: 1}}} and the path is a.b, then {c: 1} will be returned.
    """
    d = root
    for k in dotted_path.split('.'):
        d = d[k]
    return d

