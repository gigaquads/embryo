from appyratus.validation import schema, fields 
from embryo.embryo import Embryo


class {{ name|camel }}Embryo(Embryo):
    """
    An embryo for {{ name|title }}
    """

    class context_schema(fields.Schema):
        """
        The respective {{ name|title }} schema
        """
{% if schema_fields %}
{% for field in schema_fields %}

        {{ field['name'] }} = fields.{{ field['type'] }}()
        """
        {{ field['name'] }}
        """
{% endfor %}
{% else %}
        pass
{% endif %}
