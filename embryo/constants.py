import re

from appyratus.constants import STYLE_CONFIG

EMBRYO_CONSOLE_LOG_LEVEL = 'DEBUG'

RE_RENDERING_METADATA = re.compile(r'^([\w\-\_\.]+)\s*\(\s*([\w\.]*)\s*\)$')
RE_RENDERING_EMBRYO = re.compile(r'^([\w\-\_\/]+)\(([\w\.]*)\)$')

EMBRYO_PATH_ENV_VAR_NAME = 'EMBRYO_PATH'

EMBRYO_FILE_NAMES = {
    'hooks': 'hooks.py',
    'tree': 'tree.yml',
    'embryo': 'embryo.py',
    'templates': 'templates',
    'metadata-dir': '.embryo',
    'context': 'context.yml',
}

NESTED_EMBRYO_KEY = 'embryo'

PROMPT_STYLES = {
    'say': '>>>',
    'scream': 'EEE',
}
