from copy import copy
from typing import Text, Dict, Optional

from ravel import Resource, fields
from ravel.apps.cli import Cli
from appyratus.utils.dict_utils import DictUtils

from embryo.embryo import Embryo

from .command import Command
from .util import expand_path

cli = Cli(name='hatch', tagline='manage and run stored embryo commands')


@cli.action()
def run(
    request,
    name: Text,
    destination: Text = None,
    cwd: Text = None,
    **arguments,
):
    if cwd:
        cwd = expand_path(cwd)

    cmd = Command.select(Command).where(name=name.lower())(first=True)
    output = None

    if cmd is None:
        cli.log.error(f'command not found: {cmd}')
    else:
        if arguments:
            arguments = DictUtils.unflatten_keys({k.lstrip('_'): v for k, v in arguments.items()})
        context = dict(cmd.defaults, **arguments)
        context['embryo'] = {
            'destination': destination or cmd.destination,
            'name': cmd.embryo,
        }

        cmd.show(destination=destination)

        embryo = Embryo.import_embryo(cmd.embryo, context)
        embryo.hatch()


@cli.action()
def remove(request, name: Text):
    cmd = Command.select(Command).where(name=name)(first=True)
    if cmd is not None:
        cmd.show()
        cmd.log.info(f'deleting {cmd}')
        cmd.delete()


@cli.action()
def rename(
    request,
    name: Text,
    new_name: Text,
):
    cmd = Command.select(Command).where(name=name)(first=True)
    if cmd is not None:
        cmd.log.info(
            f'renaming command from {name} to {new_name}'
        )
        cmd.update(name=new_name)


@cli.action()
def upsert(
    request,
    name: Text,
    embryo: Text,
    destination: Text = None,
    cwd: Text = None,
    overwrite: bool = True,
    **defaults,
):
    # get the existing command, provided it exists. if it exists,
    # then we should perform an update below.
    existing_cmd = Command.select(Command).where(name=name.lower()).execute(first=True)

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
        DictUtils.unflatten_keys({k.lstrip('_'): v
                                  for k, v in defaults.items()})
    )

    for k, v in list(computed_defaults.items()):
        field = schema.fields[k]
        if isinstance(v, str) and v.upper() == 'NULL':
            del computed_defaults[k]
        elif v is None:
            del computed_defaults[k]
        else:
            v_processed, error = schema.fields[k].process(v)
            computed_defaults[k] = v_processed
            if error:
                cli.log.error(
                    message='error validating embryo default',
                    data={
                        'field': k,
                        'value': v,
                        'reason': error
                    }
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
            name=name, embryo=embryo, destination=destination, defaults=computed_defaults, cwd=cwd
        ).create()
        cli.log.info(f'created new command: {name}')

    cmd.show()
    return cmd


@cli.action()
def show(request, name: Optional[Text] = None, verbose: bool = False):
    if name is not None:
        cmd = Command.select(Command).where(name=name)(first=True)
        if cmd is not None:
            cmd.show(verbose=verbose)
        else:
            raise KeyError(f'command not found: {name}')
    else:
        # show all
        commands = Command.select().where().order_by(Command.name.desc)()
        for cmd in commands:
            cmd.show(verbose=verbose)
