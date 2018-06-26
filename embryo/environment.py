import re
import jinja2
import ujson
import json

from appyratus.util.text_transform import TextTransform
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

    env.filters['snake'] = TextTransform.snake
    env.filters['dash'] = TextTransform.dash
    env.filters['title'] = TextTransform.title
    env.filters['camel'] = TextTransform.camel
    env.filters['dot'] = TextTransform.dot
    env.filters['json'] = lambda obj: (
        json.dumps(ujson.loads(encoder.encode(obj)),
        indent=2, sort_keys=True
    ))

    return env
