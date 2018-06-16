from pybiz.grpc import GrpcDriver

from . import service_pb2_grpc, service_pb2


class Driver(GrpcDriver):

    def __init__(self):
        super().__init__(service_pb2, service_pb2_grpc)
