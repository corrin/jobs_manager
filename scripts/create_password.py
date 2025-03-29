from django.contrib.auth.hashers import make_password


def create_password(password: str) -> str:
    """
    Create a hashed password from a plain text password.

    :param password: The plain text password to hash.
    :return: The hashed password.
    """
    return make_password(password)
