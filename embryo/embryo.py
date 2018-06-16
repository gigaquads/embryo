from typing import Dict

from appyratus.validation import Schema

from .project import Project


class Embryo(object):
    """
    Embryo objects serve as an interface to performing various actions within
    the context of running the EmbryoGenerator.
    """

    @classmethod
    def context_schema(cls) -> Schema:
        """
        Returns an instance of a Schema class, which is applied to the context
        dict, using schema.load(context). A return value of None skips this
        process, i.e. it is optional.
        """
        return None

    def pre_create(self, context: Dict) -> None:
        """
        Perform any side-effects or preprocessing before the embryo Project and
        related objects are created. if a context_schema exists, the `context`
        argument is the marshaled result of calling `schema.load(context)`.
        This method should be overriden.
        """

    def post_create(self, project: Project, context: Dict) -> None:
        """
        Post_create is called upon the successful creation of the Project
        object. Any side-effects following the creation of the embryo in the
        filesystem can be performed here. This method should be overriden.
        """

    def apply_pre_create(self, context: Dict) -> Dict:
        """
        This method should be called only by EmbryoGenerator objects.
        """
        schema = self.context_schema()
        if schema and context:
            context = schema.load(context).data
        self.pre_create(context)
        return context

    def apply_post_create(self, project: Project, context: Dict) -> None:
        """
        This method should be called only by EmbryoGenerator objects.
        """
        self.post_create(project, context)
