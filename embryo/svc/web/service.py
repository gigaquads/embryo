from pybiz.contrib.falcon import FalconService


class EmbryoWebService(FalconService):

    @property
    def middleware(self):
        return []
