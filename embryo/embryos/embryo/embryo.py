from appyratus.validation import Schema, fields
from embryo.embryo import Embryo


class EmbryoEmbryo(Embryo):
    """
    # An embryo for generating embryos
    """

    class context_schema(Schema):
        """
        # Embryo Schema

        ## Fields
        - `name` The name of the embryo you want to create
        - `schema_fields` Schema fields to be applied to an embryo
        """
        name = fields.Str()
        schema_fields = fields.List(nested=fields.Dict())
