import re
import jinja2
import ujson
import json

from appyratus.utils import StringUtils
from appyratus.json import JsonEncoder


def build_env():
    """
    Create an instance of jinja Environment
    Templates are ideally generated from this, e.g.,

    ```
    tpl = env.from_string('Hello {{ name }}')
    tpl.render(dict(name='Johnny'))
    > "Hello Johnny"
    ```

    Custom filters are applied here
    """
    loader = jinja2.FileSystemLoader('/tmp')
    env = jinja2.Environment(autoescape=True, loader=loader, trim_blocks=True)
    encoder = JsonEncoder()

    env.filters['snake'] = StringUtils.snake
    env.filters['dash'] = StringUtils.dash
    env.filters['title'] = StringUtils.title
    env.filters['camel'] = StringUtils.camel
    env.filters['dot'] = StringUtils.dot
    env.filters['json'] = lambda obj: (
        json.dumps(ujson.loads(encoder.encode(obj)),
        indent=2, sort_keys=True
    ))

    return env
