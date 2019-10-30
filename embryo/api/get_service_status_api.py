from . import cli, repl, rpc, web


@cli()
@repl()
@rpc()
@web(http_method='GET', url_path='/status')
def get_service_status(session=None):
    return {'status': 'ok'}
