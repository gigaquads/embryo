import os

from copy import copy
from typing import Text, Dict
from ravel import CliApplication, Resource, fields
from appyratus.logging import ConsoleLoggerInterface
from appyratus.utils import DictUtils

from embryo.embryo import Embryo

from .command import Command
from .util import expand_path


cli = CliApplication(
    name='hatch',
    tagline='manage and run stored embryo commands'
)


@cli.action()
def run(
    request,
    name: Text,
    destination: Text = None,
    cwd: Text = None,
    **arguments
):
    if cwd:
        cwd = expand_path(cwd)
    
    cmd = Command.select(Command).where(name=name.lower())(first=True)
    output = None

    if cmd is None:
        cli.log.error(f'command not found: {cmd}')
    else:
        if arguments:
            arguments = DictUtils.unflatten_keys({
                k.lstrip('_'): v for k, v in arguments.items()
            })
        context = dict(cmd.defaults, **arguments)
        context['embryo'] = {
            'destination': destination or cmd.destination,
            'name': cmd.embryo,
        }

        cmd.show(destination=destination)

        embryo = Embryo.import_embryo(cmd.embryo, context)
        embryo.hatch()


@cli.action()
def upsert(
    request,
    embryo: Text,
    name: Text,
    destination: Text = None,
    cwd: Text = None,
    overwrite: bool = True,
    **defaults
):
    # get the existing command, provided it exists. if it exists,
    # then we should perform an update below.
    existing_cmd = Command.select(Command).where(
        name=name.lower()
    ).execute(first=True)

    # process default values with embryo schema fields
    embryo_obj = Embryo.import_embryo(embryo, {})
    schema = embryo_obj.context_schema()
    computed_defaults = embryo_obj.load_static_context()

    for field in schema.fields.values():
        if field.name in computed_defaults:
            continue
        default = field.default
        if default is not None:
            if callable(default):
                computed_defaults[field.name] = default()
            else:
                computed_defaults[field.name] = copy(default)

    if existing_cmd:
        computed_defaults.update(existing_cmd.defaults)

    computed_defaults.update(
        DictUtils.unflatten_keys({
            k.lstrip('_'): v for k, v in defaults.items()
        })
    )

    for k, v in list(computed_defaults.items()):
        if isinstance(v, str) and v.upper() == 'NULL':
            del computed_defaults[k]
        else:
            v_processed, error = schema.fields[k].process(v)
            computed_defaults[k] = v_processed
            if error:
                cli.log.error(
                    message='error validating embryo default',
                    data={ 'field': k, 'value': v, 'reason': error }
                )
                return

    # new or existing Command object to upsert and return:
    cmd = None

    # perform update or create...
    if existing_cmd:
        cmd = existing_cmd
        if not overwrite:
            cli.log.warning(f'command already exists: {name}')
        else:
            if computed_defaults is not None:
                cmd.defaults = computed_defaults
            if cwd:
                cmd.cwd = cwd
            if embryo:
                cmd.embryo = embryo
            if destination:
                cmd.destination = destination

            cmd.update()
            cli.log.info(f'updated existing command: {name}')
    else:
        cmd = Command(
            name=name,
            embryo=embryo,
            destination=destination,
            defaults=computed_defaults,
            cwd=cwd
        ).create()
        cli.log.info(f'created new command: {name}')

    cmd.show(verbose=False)
    return cmd


@cli.action()
def commands(
    request,
    order_by: Text = 'name',
    desc: bool = True,
    verbose: bool = False
):
    order_by = f'{order_by} {"desc" if desc else "asc"}'
    get_commands = Command.select(Command).order_by(order_by)
    for cmd in get_commands():
        cmd.show(verbose=verbose)
    