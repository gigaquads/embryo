import os
import json
import ujson

from appyratus.json import JsonEncoder

from .utils import say


class FileTypeAdapter(object):
    def __init__(self):
        pass

    @property
    def extensions(self) -> set:
        return set()

    def read(self, abs_file_path) -> object:
        raise NotImplementedError()

    def write(eslf, abs_file_path, file_obj) -> None:
        raise NotImplementedError()


class JsonAdapter(FileTypeAdapter):
    def __init__(self, indent=2, sort_keys=True):
        self._encoder = JsonEncoder()
        self._indent = indent
        self._sort_keys = sort_keys

    @property
    def extensions(self) -> set:
        return {'json'}

    def read(self, abs_file_path: str) -> dict:
        with open(abs_file_path) as json_file:
            json_str = json_file.read()
            return ujson.loads(json_str) if json_str else {}

    def write(self, abs_file_path: str, file_obj: dict) -> None:
        with open(abs_file_path, 'w') as json_file:
            json_str = json.dumps(
                ujson.loads(self._encoder.encode(file_obj)),
                indent=self._indent,
                sort_keys=self._sort_keys
            )
            json_file.write(json_str)


class FileMetadata(object):
    def __init__(self, file_obj, adapter):
        self.file_obj = file_obj
        self.adapter = adapter


class FileManager(object):
    def __init__(self):
        self._abs_path2metadata = {}
        self._ext2adapter = {}
        self._root = None

    def __getitem__(self, rel_file_path):
        key = os.path.join(self._root, rel_file_path.lstrip('/'))
        metadata = self._abs_path2metadata.get(key)
        if metadata is None:
            raise KeyError('file path not recognized')
        return metadata.file_obj

    def read(self, embryo):
        """
        Populate _abs_path2metadata by loading any file in the embryo tree for
        which there exists a FileTypeAdapter.
        """
        tree = embryo.tree
        self._root = embryo.destination

        for adapter in embryo.adapters:
            for ext in adapter.extensions:
                self._ext2adapter[ext.lower()] = adapter

        def read_recursive(node: dict):
            for parent_key, children in node.items():
                for item in children:
                    if isinstance(item, dict):
                        read_recursive(item)
                    else:
                        rel_file_path = os.path.join(parent_key, item)
                        abs_file_path = os.path.join(self._root, rel_file_path)
                        self._read_file(abs_file_path)

        for item in tree:
            read_recursive(item)

    def write(self):
        """
        Write all read files loaded into _abs_path2metadata back to the
        filesystem.
        """
        for abs_file_path, metadata in self._abs_path2metadata.items():
            say('Writing back file: {path}', path=abs_file_path)
            metadata.adapter.write(abs_file_path, metadata.file_obj)

    def _read_file(self, abs_file_path):
        """
        Read a single file into _abs_path2metadata, provided that a
        FileTypeAdapter exists for the given file type.
        """
        ext = os.path.splitext(abs_file_path)[1][1:].lower()
        adapter = self._ext2adapter.get(ext)
        if adapter and os.path.isfile(abs_file_path):
            say('Reading: {path}', path=abs_file_path)
            file_obj = adapter.read(abs_file_path)
            metadata = FileMetadata(file_obj, adapter)
            self._abs_path2metadata[abs_file_path] = metadata
