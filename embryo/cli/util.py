import os


def expand_path(path):
    return os.path.abspath(os.path.expandvars(os.path.expanduser(path)))