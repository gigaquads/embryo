import re
import jinja2

from .text_transform import TextTransform


def build_env():
    """
    Create an instance of jinja Environment
    Templates are ideally generated from this, e.g.,

    `env.from_string('Hello {{ name }}').render(dict(name='Johnny'))`

    Custom filters are applied here
    """
    loader = jinja2.FileSystemLoader('/tmp')
    env = jinja2.Environment(autoescape=True, loader=loader)

    env.filters['snake'] = TextTransform.snake
    env.filters['dash'] = TextTransform.dash
    env.filters['title'] = TextTransform.title

    import ipdb
    ipdb.set_trace()
    return env
