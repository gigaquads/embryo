from appyratus.validation import Schema


class HookManager(object):
    def __init__(self, pre_create=None, post_create=None):
        self.pre_create = pre_create
        self.post_create = post_create


class PreCreateHook(object):
    @classmethod
    def from_schema(cls, schema: Schema, context):
        """
        Using a schema, run context through it and output the resulting data
        structure.
        """
        load_data = schema().load(data=context).data
        dump_data = schema().dump(data=load_data).data
        return dump_data
