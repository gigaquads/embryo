import inspect

from .utils import say, shout


class Relationship(object):
    def __init__(
        self,
        path: str = None,
        name: str = None,
        index: int = None,
        is_nested = False
    ):
        self._path_to_dot_dir = path
        self._embryo_name = name
        self._list_index = index
        self._is_nested = is_nested

    @property
    def is_nested(self):
        return self._is_nested

    @property
    def embryo_name(self):
        return self._embryo_name

    @property
    def path_to_dot_dir(self):
        return self._path_to_dot_dir

    @property
    def list_index(self):
        return self._list_index


class RelationshipManager(object):
    def __init__(self):
        pass

    def load(self, embryo: 'Embryo'):
        relationships = {
            rel_name: rel
            for (rel_name, rel) in inspect.getmembers(
                embryo, lambda x: isinstance(x, Relationship)
            )
        }

        results = {}  # {embryo name => Embryo | List[Embryo]}

        for rel_name, rel in relationships.items():
            say('Evaluating relationship: {rel}...', rel=rel_name)
            if self._is_nested:
                assert rel.path_to_dot_dir is None
                # ^ No such thing as a dot-file path to a nested embryo
                embryos = embryo.nested[rel.embryo_name]
            else:
                embryos = embryo.dot.find(
                    name=rel.embryo_name, path=rel.path_to_dot_dir
                )
            idx = rel.list_index
            if (idx is not None) and (idx < len(embryos)):
                results[rel_name] = embryos[idx]
            else:
                results[rel_name] = embryos

        return results
