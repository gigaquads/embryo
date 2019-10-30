from embryo.svc.cli import EmbryoCliService
from embryo.svc.repl import EmbryoReplService
from embryo.svc.rpc import EmbryoRpcService
from embryo.svc.web import EmbryoWebService
from pybiz.app.middleware import GuardMiddleware
service_config = {'middleware': [GuardMiddleware()]}
cli = EmbryoCliService(echo=True, **service_config)
repl = EmbryoReplService(**service_config)
rpc = EmbryoRpcService(**service_config)
web = EmbryoWebService(**service_config)
