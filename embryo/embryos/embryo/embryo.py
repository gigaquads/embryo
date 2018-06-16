from appyratus.validation import schema, fields
from embryo.embryo import Embryo


class EmbryoEmbryo(Embryo):
    """
    An embryo for generation embryos
    """

    class EmbryoSchema(schema.Schema):
        """
        Embryo Schema
        """

        name = fields.Str()
        """
        The name of the embryo you want to create
        """

    @classmethod
    def schema_context(cls):
        return cls.EmbryoSchema
