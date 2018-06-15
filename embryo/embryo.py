from typing import Dict

from appyratus.validation import Schema

from .project import Project


class Embryo(object):

    @staticmethod
    def context_schema() -> Schema:
        return None

    def pre_create(self, context: Dict) -> None:
        pass

    def post_create(self, project: Project, context: Dict) -> None:
        pass

    def apply_pre_create(self, context: Dict) -> Dict:
        schema = self.context_schema()
        if schema and context:
            context = schema.load(context).data
        self.pre_create(context)
        return context

    def apply_post_create(self, project: Project, context: Dict) -> None:
        embryo.post_create(project, context)

