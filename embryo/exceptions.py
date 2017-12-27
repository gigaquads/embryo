class EmbryoError(Exception):
    pass


class EmbryoNotFound(EmbryoError):
    def __init__(self, embryo_path):
        message = (
            'Embryo "{}" does not exist.  make sure you have '
            'the right path to the embryo directory ').format(embryo_path)
        super().__init__(message)


class TemplateNotFound(EmbryoError):
    def __init__(self, template_name):
        message = (
            '"{}" template not found. make sure you have '
            'a templates directory in your embryo directory, containing '
            'a template file with the expected name.'.format(template_name))
        super().__init__(message)


class TemplateLoadFailed(EmbryoError):
    def __init__(self, template_name):
        message = ('failed to load "{}" template'.format(template_name))
        super().__init__(message)
