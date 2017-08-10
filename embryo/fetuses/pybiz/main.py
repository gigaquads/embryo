from embryo import Project
from embryo.util import get_script_dir

from . import templates


project = Project(
    root='test',
    tree='''
    - __init__.py
    ''',
    )


with open(get_script_dir(__file__)+'/context.yml') as ctx:
    project.build(ctx)
