from appyratus.validation import schema, fields
from embryo.embryo import Embryo


class EmbryoEmbryo(Embryo):
    """
    An embryo for generation embryos
    """

    class context_schema(schema.Schema):
        """
        Embryo Schema
        """

        name = fields.Str()
        """
        The name of the embryo you want to create
        """

        schema_fields = fields.Dict(allow_none=True, default={})
        """
        Schema fields to be applied to an embryo
        """
