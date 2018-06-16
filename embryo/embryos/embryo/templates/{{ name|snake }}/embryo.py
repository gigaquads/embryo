from appyratus.validation import schema, fields 
from embryo.embryo import Embryo


class {{ name|camel }}Embryo(Embryo):
    """
    An embryo for {{ name|title }}
    """

    class {{ name|camel }}Schema(fields.Schema):
        """
        The respective {{ name|title }} schema
        """
{% if fields %}
{% for field in fields %}
        {{ field['name'] }} = fields.{{ field['type'] }}()
        """
        {{ field['name'] }}
        """
{% endfor %}
{% else %}
        pass
{% endif %}

    def context_schema(cls):
        return cls.{{ name|camel }}Schema
