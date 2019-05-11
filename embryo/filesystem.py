import os
import json
import ujson

from appyratus.json import JsonEncoder
from appyratus.files import Yaml, Ini, Text, PythonModule

from .constants import RE_RENDERING_METADATA
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


class YamlAdapter(FileTypeAdapter):
    def __init__(self, multi=False):
        self._multi = multi

    @property
    def extensions(self) -> set:
        return {'yml', 'yaml'}

    def read(self, abs_file_path: str) -> dict:
        return Yaml.from_file(file_path=abs_file_path, multi=self._multi)

    def write(self, abs_file_path: str, file_obj: dict) -> None:
        Yaml.to_file(file_path=abs_file_path, data=file_obj, multi=self._multi)


class IniAdapter(FileTypeAdapter):
    @property
    def extensions(self) -> set:
        return {'ini', 'cfg'}

    def read(self, abs_file_path: str) -> dict:
        return Ini.from_file(file_path=abs_file_path)

    def write(self, abs_file_path: str, data) -> None:
        Ini.to_file(file_path=abs_file_path, data=data)


class TextAdapter(FileTypeAdapter):
    @property
    def extensions(self) -> set:
        return {'txt'}

    def read(self, abs_file_path: str) -> str:
        return Text.from_file(file_path=abs_file_path)

    def write(self, abs_file_path: str, contents: str) -> None:
        Text.to_file(file_path=abs_file_path, contents=contents)


class HtmlAdapter(TextAdapter):
    @property
    def extensions(self) -> set:
        return {'htm', 'html'}


class MarkdownAdapter(TextAdapter):
    @property
    def extensions(self) -> set:
        return {'md'}


class CssAdapter(TextAdapter):
    @property
    def extensions(self) -> set:
        return {'css'}


class PythonAdapter(TextAdapter):
    @property
    def extensions(self) -> set:
        return {'py'}

    def read(self, abs_file_path: str) -> str:
        return PythonModule.from_file(file_path=abs_file_path)

    def write(self, abs_file_path: str, contents: str = None) -> None:
        PythonModule.to_file(file_path=abs_file_path, contents=contents)


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

        def read_recursive(node: dict, path_key: str):
            if isinstance(node, str):
                match = RE_RENDERING_METADATA.match(node)
                if match:
                    self._read_file(path_key)
                else:
                    abs_file_path = os.path.join(path_key, node)
                    self._read_file(abs_file_path)
                return
            elif isinstance(node, dict):
                for parent_key, children in node.items():
                    if not children:
                        continue
                    child_path_key = os.path.join(path_key, parent_key)
                    read_recursive(children, child_path_key)
            elif isinstance(node, list):
                for child in node:
                    child_path_key = os.path.join(path_key)
                    read_recursive(child, child_path_key)

        if tree:
            read_recursive(tree, self._root)

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
        if not adapter:
            say(
                "Adapter not found for extension '{}' [{}]".format(
                    ext, abs_file_path
                )
            )
        if adapter and os.path.isfile(abs_file_path):
            say('Reading: {path}', path=abs_file_path)
            file_obj = adapter.read(abs_file_path)
            metadata = FileMetadata(file_obj, adapter)
            self._abs_path2metadata[abs_file_path] = metadata
