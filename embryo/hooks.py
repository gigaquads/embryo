from appyratus.schema import Schema


class HookManager(object):
    def __init__(self, pre_create=None, post_create=None):
        self.pre_create = pre_create
        self.post_create = post_create


class PreCreateHook(object):
    @classmethod
    def resolve_context(cls, context, key):
        val = context['args'].get(key, context.get(key))
        context[key] = val
        return val

    @classmethod
    def from_schema(cls, schema: Schema, context):
        data = schema().load(data=context['args']).data
        for key, value in data.items():
            val = data.get(key, context.get(key))
            context[key] = val
        return context
