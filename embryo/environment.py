import re
import jinja2


def snaked(value):
    """
    Snaked filter for jinja to provide snake casing `such_as_this`
    """
    return re.sub(r'([a-z])([A-Z])', r'\1_\2', value).lower()


def dashed(value):
    """
    Dashed filter for jinja to provide lisp-style casing `such-as-this`
    """
    return re.sub(r'([a-z])([A-Z])', r'\1-\2', value).lower()


def build_env():
    """
    Create an instance of jinja Environment
    Templates are ideally generated from this, e.g.,

    `env.from_string('Hello {{ name }}').render(dict(name='Johnny'))`

    Custom filters are applied here
    """
    loader = jinja2.FileSystemLoader('/tmp')
    env = jinja2.Environment(autoescape=True, loader=loader)

    env.filters['snaked'] = snaked
    env.filters['dashed'] = dashed

    return env
