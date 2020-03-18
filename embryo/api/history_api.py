from . import cli

from appyratus.cli import CliProgram, Subparser, PositionalArg, OptionalArg, FlagArg, Parser

from embryo.history import History

@cli(name='history')
def user_gets_history(session: 'Session' = None):
    """
    # Gets History
    A user gets history for a given project's embryo context
    """
    history = History.read_context()
    for event_at, command in history:
        print(f'{event_at} {command}')
