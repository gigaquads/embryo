from pybiz.grpc import GrpcService

from .driver import Driver


class Service(GrpcService):

    def __init__(self, **kwargs):
        super().__init__(Driver(), **kwargs)

{% for method_name in methods %}
    def {{ method_name }}(self, request, context):
        pass
{% endfor %}
