from typing import Dict, Text

from tabulate import tabulate
from appyratus.utils import DictUtils, StringUtils
from ravel import Resource, fields

from embryo.embryo import Embryo


class Command(Resource):
    created_at = fields.DateTime(required=True, nullable=False, default=True)
    embryo = fields.String(required=True)
    defaults = fields.Dict(required=True, nullable=False, default={})
    cwd = fields.String(nullable=True, default=lambda: None)
    name = fields.String(required=True)
    destination = fields.String(required=True, default='.')

    def show(self, destination=None, verbose=False):
        embryo = Embryo.import_embryo(self.embryo, {})
        schema = embryo.context_schema()

        context = {}
        context_vars = set()
        optional_context_vars = set()
        for field in schema.fields.values():
            if field.name == 'embryo':
                continue
            if field.default and field.name not in self.defaults:
                if callable(field.default):
                    context[field.name] = field.default()
                else:
                    context[field.name] = field.default
            elif field.name not in self.defaults:
                if field.required:
                    context_vars.add(field.name)
                else:
                    optional_context_vars.add(field.name)

        context.update(self.defaults)

        cmd_str = f'\n➥ hatch run {self.name}\n'

        for k, v in sorted(context.items()):
            v = self.app.json.encode(v)
            if len(v) > 80:
                v = f'{v[:40]} ⋯ {v[-40:]}'
            cmd_str += f'   --{k} {v}\n'

        for k in sorted(context_vars):
            cmd_str += f'   --{k} ${k.upper()}\n'

        for k in sorted(optional_context_vars):
            cmd_str += f'   [--{k} ${k.upper()}]\n'

        if not verbose:
            print(cmd_str)