import os
from os.path import (
    exists,
    join,
)
from typing import (
    Dict,
    Text,
)

from appyratus.files import (
    Css,
    File,
    Html,
    Ini,
    Json,
    Markdown,
    PythonModule,
    Shell,
)
from appyratus.files import Text as TextFile
from appyratus.files import Yaml
from appyratus.utils import PathUtils

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

    def write(self, abs_path: Text, data=None) -> None:
        raise NotImplementedError()

    def load(self, data) -> object:
        return data


class FileAdapter(FileTypeAdapter):
    """
    # File Adapter
    Generic file adapter when no other is appropriate
    """

    @property
    def extensions(self) -> set:
        return {None}

    def read(self, abs_path: Text) -> object:
        return File.read(abs_path)

    def write(self, abs_path: Text, data) -> None:
        File.write(abs_path, data)


class JsonAdapter(FileTypeAdapter):

    def __init__(self, indent=2, sort_keys=True):
        self._indent = indent
        self._sort_keys = sort_keys

    @property
    def extensions(self) -> set:
        return Json.extensions()

    def read(self, abs_path: Text) -> dict:
        return Json.read(abs_path)

    def write(self, abs_path: Text, data) -> None:
        Json.write(
            abs_path,
            Json.load(Json.dump(data)),
            ident=self._indent,
            sort_keys=self._sort_keys
        )


class YamlAdapter(FileTypeAdapter):

    def __init__(self, multi=False):
        self._multi = multi

    @property
    def extensions(self) -> set:
        return Yaml.extensions()

    def load(self, data):
        return Yaml.load(data, multi=self._multi)

    def read(self, abs_path: Text) -> dict:
        return Yaml.read(path=abs_path, multi=self._multi)

    def write(self, abs_path: Text, data) -> None:
        Yaml.write(path=abs_path, data=data, multi=self._multi)


class IniAdapter(FileTypeAdapter):

    @property
    def extensions(self) -> set:
        return Ini.extensions()

    def read(self, abs_path: Text) -> dict:
        return Ini.read(path=abs_path)

    def write(self, abs_path: Text, data=None) -> None:
        Ini.write(path=abs_path, data=data)


class TextAdapter(FileTypeAdapter):

    @property
    def extensions(self) -> set:
        return TextFile.extensions()

    def read(self, abs_path: Text) -> Text:
        return TextFile.read(path=abs_path)

    def write(self, abs_path: Text, data=None) -> None:
        TextFile.write(path=abs_path, data=data)


class HtmlAdapter(TextAdapter):

    @property
    def extensions(self) -> set:
        return Html.extensions()


class MarkdownAdapter(TextAdapter):

    @property
    def extensions(self) -> set:
        return Markdown.extensions()


class CssAdapter(TextAdapter):

    @property
    def extensions(self) -> set:
        return Css.extensions()


class ShellAdapter(TextAdapter):

    @property
    def extensions(self) -> set:
        return Shell.extensions()


class PythonAdapter(TextAdapter):

    def __init__(
        self,
        preserve_comments: bool = True,
        format_code: bool = True,
        style_config: Dict = None
    ):
        self._preserve_comments = preserve_comments
        self._format_code = format_code
        self._style_config = style_config

    @property
    def extensions(self) -> set:
        return PythonModule.extensions()

    def read(self, abs_path: Text) -> Text:
        return PythonModule.read(path=abs_path, preserve_comments=self._preserve_comments)

    def write(self, abs_path: Text, data=None) -> None:
        PythonModule.write(
            path=abs_path,
            data=data,
            restore_comments=self._preserve_comments,
            format_code=self._format_code,
            style_config=self._style_config
        )


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
        return join(self._root, key.lstrip('/'))

    def __contains__(self, rel_file_path):
        return self.build_abs_path(rel_file_path) in self.path2metadata.keys()

    def _touch_filesystem(self, root, dir_paths, file_paths) -> None:
        """
        Creates files and directories in the file system. This will not
        overwrite anything.
        """
        if not exists(root):
            os.makedirs(root)
            say('Creating directory: {path}', path=root)
        for dir_path in dir_paths:
            path = join(root, './{}'.format(dir_path))
            if not exists(path):
                say('Creating directory: {path}', path=path)
                os.makedirs(path)
        for fpath in file_paths:
            path = join(root, './{}'.format(fpath))
            if not os.path.isfile(path) and not path.endswith('.embryo'):
                say('Touching file: {path}', path=path)
                open(path, 'a').close()

    def read(self, embryo):
        """
        Populate _abs_path2metadata by loading any file in the embryo tree for
        which there exists a FileTypeAdapter.
        """
        tree = embryo.tree
        self._root = embryo.destination

        def read_recursive(node: Dict, path_key: Text):
            if isinstance(node, str):
                match = RE_RENDERING_METADATA.match(node)
                if match:
                    abs_path = path_key
                else:
                    abs_path = join(path_key, node)
                self._read_file(abs_path, embryo)
                return
            elif isinstance(node, dict):
                for parent_key, children in node.items():
                    if not children:
                        continue
                    child_path_key = join(path_key, parent_key)
                    read_recursive(children, child_path_key)
            elif isinstance(node, list):
                for child in node:
                    child_path_key = join(path_key)
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

    def _read_file(self, abs_path, embryo):
        """
        Read a single file into _abs_path2metadata, provided that a
        FileTypeAdapter exists for the given file type.
        """
        ext = PathUtils.get_extension(abs_path)
        adapter = embryo.ext2adapter.get(ext or None)
        if not adapter:
            say(f"Adapter not found for extension '{ext}' [{abs_path}]")
        if adapter and os.path.isfile(abs_path):
            say('Reading: {path}', path=abs_path)
            file_obj = adapter.read(abs_path)
            metadata = FileMetadata(file_obj, adapter)
            self._abs_path2metadata[abs_path] = metadata
