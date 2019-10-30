from typing import Text

from appyratus.files import Json
from appyratus.utils import DictUtils, TimeUtils


class History(object):

    @classmethod
    def read_context(cls, path: Text = None):
        if path is None:
            path = '.embryo/context.json'
        context = Json.read(path)
        embryo_commands = cls.parse_context(context)
        embryo_commands.sort(key=lambda tup: tup[0])
        used_commands = []
        for timestamp, command in embryo_commands:
            if command in used_commands:
                continue
            used_commands.append((TimeUtils.from_timestamp(timestamp), command))
        return used_commands

    @classmethod
    def parse_context(cls, context):
        commands = []
        if context is None:
            context = {}
        for embryo, contexts in context.items():
            for context in contexts:
                embryo_data = context['embryo']
                del context['embryo']
                flat_context = DictUtils.flatten_keys(context)
                context_args = [
                    '--{} {}'.format(k, v) for k, v in flat_context.items()
                    if v is not None
                ]
                command = 'embryo {} {} {}'.format(
                    embryo_data['action'], embryo, ' '.join(context_args)
                )
                timestamp = embryo_data['timestamp']
                commands.append((timestamp, command))

        return commands
