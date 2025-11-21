import hashlib


class SecurityManager:
    def __init__(self):
        self.users = {
            'root': {'password': 'root', 'group': 'root'},
            'alice': {'password': 'alice', 'group': 'devs'},
            'bob': {'password': 'bob', 'group': 'devs'}
        }
        self.current_user = 'root'
        self.integrity_registry = {}

    def authenticate(self, username, password):
        user = self.users.get(username)
        if user and user['password'] == password:
            self.current_user = username
            return True, f"Usuario {username} autenticado"
        return False, "Credenciales inválidas"

    def get_user_group(self, username):
        user = self.users.get(username)
        return user['group'] if user else 'guest'

    def list_users(self):
        return [{'user': u, 'group': info['group']} for u, info in self.users.items()]

    def store_integrity_hash(self, key, content):
        self.integrity_registry[key] = hashlib.sha256(content.encode()).hexdigest()

    def verify_integrity(self, key, content):
        expected = self.integrity_registry.get(key)
        if not expected:
            return False, "No hay hash registrado"
        current = hashlib.sha256(content.encode()).hexdigest()
        return (expected == current, "Integridad verificada" if expected == current else "Integridad comprometida")
