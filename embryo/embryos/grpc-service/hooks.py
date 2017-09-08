import os
import importlib
import subprocess as sp

from pybiz.grpc import GrpcDriver


def pre_create(project, context, tree, templates):
    dest = context['args']['destination']
    command = ' '.join([
        'python -m grpc_tools.protoc',
        '-I {dest}',
        '--python_out={dest}',
        '--grpc_python_out={dest}',
        '{dest}/service.proto'
        ]).format(dest=dest)

    print(command)
    output = sp.getoutput(command)
    if output:
        print(output)

    old_cwd = os.getcwd()
    os.chdir(dest)

    service_pb2 = importlib.import_module('service_pb2')
    service_pb2_grpc = importlib.import_module('service_pb2_grpc')
    driver = GrpcDriver(service_pb2, service_pb2_grpc)

    os.chdir(old_cwd)

    context['methods'] = driver.methods
