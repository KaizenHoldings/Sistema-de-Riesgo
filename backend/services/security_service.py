import bcrypt

class SecurityService:
    @staticmethod
    def hash_password(password: str) -> str:
        """Genera un hash seguro para la contraseña."""
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')

    @staticmethod
    def verify_password(password: str, hashed_password: str) -> bool:
        """Verifica si la contraseña coincide con el hash almacenado."""
        try:
            return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))
        except Exception:
            return False
