from appyratus.validation import fields
from embryo import Embryo


class EmbryoEmbryo(Embryo):
    """
    # An embryo for generating embryos
    """

    class context_schema(Embryo.Schema):
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
        Allow schema fields to be passed in as a string, that constructs a
        dictionary with the value as the field name and `Anything` as the type.
        And a dictionary, a presumed schema field structure, will be
        transformed to a list with itself being a member.
        """
        schema_fields = self.context.get('schema_fields')
        if isinstance(schema_fields, str):
            schema_fields = dict(name=schema_fields, type='Anything')
        if isinstance(schema_fields, dict):
            schema_fields = [schema_fields]
        self.context['schema_fields'] = schema_fields
