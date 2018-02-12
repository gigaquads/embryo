from appyratus.schema import Schema


class HookManager(object):
    def __init__(self, pre_create=None, post_create=None):
        self.pre_create = pre_create
        self.post_create = post_create


class PreCreateHook(object):
    @classmethod
    def from_schema(cls, schema: Schema, context):
        return schema().load(data=context).data
