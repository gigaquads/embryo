import pybiz.falcon

from pybiz.falcon.middleware import RequestBinder, JsonTranslator
from pybiz import Dao, BizObject


class Api(pybiz.falcon.Api):

    @property
    def middleware(self):
        return [
            RequestBinder([Dao, BizObject]),
            JsonTranslator(encoder=None),
            ]

    def unpack(self, request, **kwargs):
        """
        This method defines how thw request and response arguments to Falcon
        api request handler methods are "unpacked" into the argument lists
        received by said methods when decorated with @api.post, etc.). The
        return value is a tuple, where the first element is the args list and
        the second is the kwargs dict.
        """
        args = (request,)
        kwargs.update(request.json)
        return (args, kwargs)


#$
## Global Api Instance
##

api = Api()
