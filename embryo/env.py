from appyratus.env import Environment
from appyratus.schema import fields


class EmbryoEnvironment(Environment):
    # XXX commented out data path, currently we do not have any embryo data
    #EMBRYO_DATA_PATH = fields.FilePath(required=True)
    EMBRYO_MANIFEST_FILEPATH = fields.FilePath(required=True)

    #@property
    #def data_path(self):
    #    return self['EMBRYO_DATA_PATH']

    @property
    def manifest_filepath(self):
        return self['EMBRYO_MANIFEST_FILEPATH']
