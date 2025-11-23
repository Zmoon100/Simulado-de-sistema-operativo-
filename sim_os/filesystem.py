from dataclasses import dataclass, field
import hashlib


@dataclass
class PermissionSet:
    owner: str = "root"
    group: str = "root"
    perms: str = "rwxr-x---"


@dataclass
class FileEntry:
    content: str = ""
    permissions: PermissionSet = field(default_factory=PermissionSet)
    hash: str = ""


class FileSystem:
    def __init__(self, security_manager=None):
        self.files = {}
        self.directories = {'/': []}
        self.current_directory = '/'
        self.security_manager = security_manager

    def create_file(self, filename, content=""):
        path = self._get_full_path(filename)
        if path in self.files:
            return False, "El archivo ya existe"
        owner = self.security_manager.current_user if self.security_manager else "root"
        entry = FileEntry(
            content=content,
            permissions=PermissionSet(owner=owner, group="devs"),
            hash=self._calc_hash(content)
        )
        self.files[path] = entry
        self._add_to_directory(path)
        if self.security_manager:
            self.security_manager.store_integrity_hash(f"file_{path}", content)
        return True, f"Archivo '{filename}' creado"

    def create_directory(self, dirname):
        path = self._get_full_path(dirname)
        if path in self.directories:
            return False, "El directorio ya existe"
        self.directories[path] = []
        parent = '/'.join(path.split('/')[:-1]) or '/'
        if parent not in self.directories:
            self.directories[parent] = []
        name = path.split('/')[-1]
        if name not in self.directories[parent]:
            self.directories[parent].append(name)
        owner = self.security_manager.current_user if self.security_manager else "root"
        if self.security_manager:
            self.security_manager.store_integrity_hash(f"dir_{path}", owner)
        return True, f"Directorio '{dirname}' creado"

    def change_directory(self, path):
        if not path:
            return False, "Ruta requerida"
        target = path if path.startswith('/') else f"{self.current_directory.rstrip('/')}/{path}"
        parts = [p for p in target.split('/') if p != '']
        stack = []
        for p in parts:
            if p == '.':
                continue
            if p == '..':
                if stack:
                    stack.pop()
                continue
            stack.append(p)
        normalized = '/' + '/'.join(stack)
        if normalized == '':
            normalized = '/'
        if normalized in self.directories:
            self.current_directory = normalized
            return True, normalized
        return False, "Directorio no existe"

    def get_cwd(self):
        return self.current_directory

    def read_file(self, filename):
        path = self._get_full_path(filename)
        entry = self.files.get(path)
        if not entry:
            return None, "Archivo no encontrado"
        if not self._has_permission(path, 'r'):
            return None, "Permiso denegado"
        return entry.content, None

    def write_file(self, filename, content):
        path = self._get_full_path(filename)
        entry = self.files.get(path)
        if not entry:
            return False, "Archivo no encontrado"
        if not self._has_permission(path, 'w'):
            return False, "Permiso denegado"
        entry.content = content
        entry.hash = self._calc_hash(content)
        if self.security_manager:
            self.security_manager.store_integrity_hash(f"file_{path}", content)
        return True, f"Archivo '{filename}' actualizado"

    def delete_file(self, filename):
        path = self._get_full_path(filename)
        entry = self.files.get(path)
        if not entry:
            return False, "Archivo no encontrado"
        if not self._has_permission(path, 'w'):
            return False, "Permiso denegado"
        del self.files[path]
        self._remove_from_directory(path)
        return True, f"Archivo '{filename}' eliminado"

    def list_directory(self):
        entries = []
        names = self.directories.get(self.current_directory, [])
        for name in names:
            entries.append(f"{self.current_directory.rstrip('/')}/{name}")
        return entries

    def get_file_info(self, path):
        entry = self.files.get(path)
        if not entry:
            return None
        return {
            'path': path,
            'owner': entry.permissions.owner,
            'group': entry.permissions.group,
            'perms': entry.permissions.perms,
            'hash': entry.hash
        }

    def get_path_info(self, path):
        info = self.get_file_info(path)
        if info:
            info['type'] = 'file'
            return info
        if path in self.directories:
            owner = self.security_manager.current_user if self.security_manager else "root"
            return {
                'path': path,
                'owner': owner,
                'group': self.security_manager.get_user_group(owner) if self.security_manager else 'root',
                'perms': 'rwxr-x---',
                'hash': '',
                'type': 'dir'
            }
        return None

    def _calc_hash(self, content):
        return hashlib.sha256(content.encode()).hexdigest()

    def _has_permission(self, path, mode):
        if not self.security_manager:
            return True
        entry = self.files.get(path)
        if not entry:
            return False
        perms = entry.permissions.perms
        user = self.security_manager.current_user
        if user == entry.permissions.owner:
            scope = perms[:3]
        elif self.security_manager.get_user_group(user) == entry.permissions.group:
            scope = perms[3:6]
        else:
            scope = perms[6:]
        mapping = {'r': scope[0] == 'r', 'w': scope[1] == 'w', 'x': scope[2] == 'x'}
        return mapping.get(mode, False)

    def _get_full_path(self, filename):
        if filename.startswith('/'):
            return filename
        return f"{self.current_directory.rstrip('/')}/{filename}"

    def _add_to_directory(self, path):
        dir_path = '/'.join(path.split('/')[:-1]) or '/'
        if dir_path not in self.directories:
            self.directories[dir_path] = []
        filename = path.split('/')[-1]
        if filename not in self.directories[dir_path]:
            self.directories[dir_path].append(filename)

    def _remove_from_directory(self, path):
        dir_path = '/'.join(path.split('/')[:-1]) or '/'
        filename = path.split('/')[-1]
        if dir_path in self.directories and filename in self.directories[dir_path]:
            self.directories[dir_path].remove(filename)
