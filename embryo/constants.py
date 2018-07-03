import re

RE_RENDERING_METADATA = re.compile(r'^(\w+)\s*\(\s*([\w\.]*)\s*\)$')
RE_RENDERING_EMBRYO = re.compile(r'^([\w\-\_\/]+)\(([\w\.]*)\)$')

EMBRYO_PATH_ENV_VAR_NAME = 'EMBRYO_PATH'

EMBRYO_FILE_NAMES = {
    'hooks': 'hooks.py',
    'tree': 'tree.yml',
    'embryo': 'embryo.py',
    'context': 'context.yml',
    'templates': 'templates',
    'metadata-dir': '.embryo',
}

STYLE_CONFIG = {
    'BASED_ON_STYLE': 'pep8',
    'COLUMN_LIMIT': 80,
    'COALESCE_BRACKETS': True,
    'ALLOW_MULTILINE_DICTIONARY_KEYS': False,
    'ALIGN_CLOSING_BRACKET_WITH_VISUAL_INDENT': True,
    'SPLIT_ARGUMENTS_WHEN_COMMA_TERMINATED': True,
    'SPLIT_BEFORE_DICT_SET_GENERATOR': True,
    'BLANK_LINE_BEFORE_NESTED_CLASS_OR_DEF': True,
    'SPLIT_BEFORE_FIRST_ARGUMENT': True,
    'DEDENT_CLOSING_BRACKETS': True,
    'CONTINUATION_INDENT_WIDTH': 8,
    'INDENT_WIDTH': 4,
}

PROMPT_STYLES = {
    'say': '>>>',
    'scream': 'EEE',
}
