from appyratus.validation import Schema, fields 
from embryo.embryo import Embryo


class {{ name|camel }}Embryo(Embryo):
    """
    # {{name|title }} Embryo
    """

    class context_schema(Schema):
        """
        # Context Schema
        The respective {{ name|title }} schema
{% if schema_fields %}
        
        ## Fields
{% for field in schema_fields %}
        * `{{ field['name']|snake }}`: {{ field.get('description', 'TODO') }}
{% endfor %}
{% endif %}
        """
{% if schema_fields %}
{% for field in schema_fields %}
        {{ field['name']|snake }} = fields.{{ field['type']|camel }}()
{% endfor %}
{% else %}
        pass
{% endif %}
