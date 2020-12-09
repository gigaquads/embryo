from typing import Dict, Text

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

    def prepare(self, destination: Text = None, args: Dict = None) -> Text:
        context_json = self.app.json.encode(args)
        return (
            f"embryo hatch {self.embryo}"
            f"  -d '{destination}'\n"
            f"  -c {context_json}\n"
        )

    def show(self, destination=None, verbose=False):
        embryo = Embryo.import_embryo(self.embryo, {})
        schema = embryo.context_schema()

        context = {}
        context_vars = set()
        for field in schema.fields.values():
            if field.default and field.name not in self.defaults:
                if callable(field.default):
                    context[field.name] = field.default()
                else:
                    context[field.name] = field.default
            elif field.name not in self.defaults and field.required:
                context_vars.add(field.name)

        context.update(self.defaults)

        if 'embryo' in context:
            del context['embryo']
        if 'embryo' in context_vars:
            context_vars.remove('embryo')

        if not verbose:
            self.app.log.info(
                message=f'hatching {self.embryo} embryo as {self.name}',
                data={
                    'destination': destination or self.destination,
                    'context': context,
                    'variables': context_vars
                }
            )