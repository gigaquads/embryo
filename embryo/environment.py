from appyratus.utils.template_utils import TemplateEnvironment


def build_env():
    """
    Create an instance of jinja Environment
    """
    return TemplateEnvironment(search_path='/tmp')
