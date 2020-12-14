from typing import Text

from appyratus.files import Json
from appyratus.utils.dict_utils import DictUtils
from appyratus.utils.time_utils import TimeUtils

from embryo.dot import DotFileManager


class History(object):
    """
    # History
    Project the state of the embryo context file in time sequence
    """

    @classmethod
    def read_context(cls, path: Text = None):
        _, context, _, _ = DotFileManager.get_context(path)
        embryo_commands = cls.parse_context(context)
        embryo_commands.sort(key=lambda tup: tup[0])
        used_commands = []
        for timestamp, command in embryo_commands:
            if command in used_commands:
                continue
            ts = TimeUtils.from_timestamp(timestamp)
            used_commands.append((ts, command))
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
