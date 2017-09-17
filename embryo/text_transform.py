import re


class TextTransform(object):
    """
    Transform Text in various ways
    """

    @classmethod
    def normalize(cls, value):
        """
        Normalize a value a word-only character string with spaces
        - Split up possible class names
        - Replace all non-word characters with spaces
        - Reduce spacing
        """
        value = cls.split_class_name(value)
        value = cls.non_word_to_space(value)
        value = cls.reduce_spacing(value)
        return value

    @classmethod
    def split_class_name(cls, value):
        """
        Split a class name into readable parts
        - Replace all cases of "Az" with " Az"
        - Replace all cases of "aZ" with "a Z"
        - Strip the remaining space
        E.g., with the string "SaveAPlant", it has the following transformations
        -> " SaveA Plant"
        -> " Save A Plant"
        -> "Save A Plant"

        This will additionally preserve constants
        """
        value = re.sub(r'([A-Z][a-z])', r' \1', value)
        value = re.sub(r'([a-z])([A-Z])', r'\1 \2', value)
        return value.strip()

    @classmethod
    def non_word_to_space(cls, value):
        return re.sub(r'[\W_]', ' ', value)

    @classmethod
    def reduce_spacing(cls, value):
        return re.sub(r'\s+', ' ', value).strip()

    @classmethod
    def snake(cls, value):
        """
        Snake case `such_as_this`
        """
        return re.sub(r'\s', r'_', cls.normalize(value)).lower()

    @classmethod
    def title(cls, value):
        """
        Title `Such As This`
        """
        return str.title(cls.normalize(value))

    @classmethod
    def dash(cls, value):
        """
        Dash case `such-as-this`
        """
        return re.sub(r'\s', r'-', cls.normalize(value)).lower()
