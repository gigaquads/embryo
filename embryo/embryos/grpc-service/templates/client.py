from pybiz.grpc import GrpcClient

from .driver import Driver


class Client(GrpcClient):

    def __init__(self, **kwargs):
        super().__init__(Driver(), **kwargs)

{% for method_name in methods %}
    def {{ method_name }}(self, *args, **kwargs):
        pass
{% endfor %}
