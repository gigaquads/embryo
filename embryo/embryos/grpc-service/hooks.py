import subprocess as sp


def pre_create(project, context, tree, templates):
    command = ' '.join([
        'python -m grpc_tools.protoc',
        '-I {protobuf_dir}',
        '--python_out={output_dir}',
        '--grpc_python_out={output_dir}',
        '{protobuf_dir}/service.proto'
        ]).format(
            protobuf_dir='.',
            output_dir='.',
            )
    #print(command)
    #print(sp.getoutput(command))


def post_create(project, context):
    print('Inside post_create')
