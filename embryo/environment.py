import re
import jinja2
import ujson
import json

from appyratus.utils import StringUtils, TemplateEnvironment
from appyratus.json import JsonEncoder


def build_env():
    """
    Create an instance of jinja Environment
    """
    return TemplateEnvironment(search_path='/tmp')
