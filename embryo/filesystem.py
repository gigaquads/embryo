from typing import Text
import os

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

    def read(self, abs_path) -> object:
        raise NotImplementedError()

    def write(self, abs_path: Text, data = None) -> None:
        raise NotImplementedError()


class JsonAdapter(FileTypeAdapter):
    def __init__(self, indent=2, sort_keys=True):
        self._encoder = JsonEncoder()
        self._indent = indent
        self._sort_keys = sort_keys

    @property
    def extensions(self) -> set:
        return {'json'}

    def read(self, abs_path: Text) -> dict:
        return Json.read(abs_path)

    def write(self, abs_path: Text, data) -> None:
        Json.write(
            Json.load(self._encoder.encode(data)),
            ident=self._indent,
            sort_keys=self._sort_keys
        )


class YamlAdapter(FileTypeAdapter):
    def __init__(self, multi=False):
        self._multi = multi

    @property
    def extensions(self) -> set:
        return {'yml', 'yaml'}

    def read(self, abs_path: Text) -> dict:
        return Yaml.read(path=abs_path, multi=self._multi)

    def write(self, abs_path: Text, data) -> None:
        Yaml.write(path=abs_path, data=data, multi=self._multi)


class IniAdapter(FileTypeAdapter):
    @property
    def extensions(self) -> set:
        return {'ini', 'cfg'}

    def read(self, abs_path: Text) -> dict:
        return Ini.read(path=abs_path)

    def write(self, abs_path: Text, data = None) -> None:
        Ini.write(path=abs_path, data=data)


class TextAdapter(FileTypeAdapter):
    @property
    def extensions(self) -> set:
        return {'txt'}

    def read(self, abs_path: Text) -> Text:
        return Text.read(path=abs_path)

    def write(self, abs_path: Text, data = None) -> None:
        Text.write(path=abs_path, data=data)


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

    def read(self, abs_path: Text) -> Text:
        return PythonModule.read(path=abs_path)

    def write(self, abs_path: Text, data=None) -> None:
        PythonModule.write(path=abs_path, data=data)


class FileMetadata(object):
    def __init__(self, file_obj, adapter):
        self.file_obj = file_obj
        self.adapter = adapter


class FileManager(object):
    def __init__(self):
        self._abs_path2metadata = {}
        self._ext2adapter = {}
        self._root = None

    @property
    def path2metadata(self):
        return self._abs_path2metadata

    def __getitem__(self, rel_file_path: Text):
        metadata = self.get_metadata(self.build_abs_path(rel_file_path))
        if metadata is None:
            raise KeyError('file path not recognized')
        return metadata.file_obj

    def get_metadata(self, key):
        return self.path2metadata.get(key)

    def find_metadata(self, key):
        res = self.get_metadata(key)
        if res:
            return res
        known_keys = list(self.path2metadata.keys())
        matches = {}
        for k in known_keys:
            if key in k:
                matches[k] = self.get_metadata(k)
        return matches

    def build_abs_path(self, key):
        return os.path.join(self._root, key.lstrip('/'))

    def __contains__(self, rel_file_path):
        return self.build_abs_path(rel_file_path) in self.path2metadata.keys()

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

        def read_recursive(node: dict, path_key: Text):
            if isinstance(node, str):
                match = RE_RENDERING_METADATA.match(node)
                if match:
                    self._read_file(path_key)
                else:
                    abs_path = os.path.join(path_key, node)
                    self._read_file(abs_path)
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
        for abs_path, metadata in self._abs_path2metadata.items():
            say('Writing back file: {path}', path=abs_path)
            metadata.adapter.write(abs_path, metadata.file_obj)

    def _read_file(self, abs_path):
        """
        Read a single file into _abs_path2metadata, provided that a
        FileTypeAdapter exists for the given file type.
        """
        ext = os.path.splitext(abs_path)[1][1:].lower()
        adapter = self._ext2adapter.get(ext)
        if not adapter:
            say("Adapter not found for extension '{}' [{}]".format(ext, abs_path))
        if adapter and os.path.isfile(abs_path):
            say('Reading: {path}', path=abs_path)
            file_obj = adapter.read(abs_path)
            metadata = FileMetadata(file_obj, adapter)
            self._abs_path2metadata[abs_path] = metadata
