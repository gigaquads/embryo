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
        schema_fields = fields.List(nested=fields.Dict(), default=[])

    def pre_create(self):
        """
        The most complete schema fields is a dictionary of data, including name
        , description, and even type.  However, sometimes you want to simply
        and quickly define a few fields without being specific as to what they
        are.  All of this is of course optional.

        If a string is provided then it will be cast into basic schema_fields
        with name only.
        """
        schema_fields = self.context.get('schema_fields', [])
        if isinstance(schema_fields, str):
            self.context['schema_fields'] = [dict(name=schema_fields)]
