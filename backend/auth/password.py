import bcrypt

def get_password_hash(password: str) -> str:
    # Ensure password isn't larger than 72 bytes to avoid standard bcrypt limits
    password_bytes = password[:72].encode('utf-8')
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password_bytes, salt).decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    password_bytes = plain_password[:72].encode('utf-8')
    return bcrypt.checkpw(password_bytes, hashed_password.encode('utf-8'))
