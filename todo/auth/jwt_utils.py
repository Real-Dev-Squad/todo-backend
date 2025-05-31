import jwt
from django.conf import settings
from todo.exceptions.auth_exceptions import TokenExpiredError, TokenInvalidError


def verify_jwt_token(token: str) -> dict:
    """
    Verify and decode the JWT token using the RSA public key.

    Args:
        token (str): The JWT token to verify

    Returns:
        dict: The decoded token payload

    Raises:
        TokenExpiredError: If token has expired
        TokenInvalidError: If token is invalid
    """
    if not token or not token.strip():
        raise TokenInvalidError()

    try:
        public_key = settings.JWT_AUTH["PUBLIC_KEY"]
        algorithm = settings.JWT_AUTH["ALGORITHM"]

        if not public_key:
            raise TokenInvalidError()

        payload = jwt.decode(
            token,
            public_key,
            algorithms=[algorithm],
            options={"verify_signature": True, "verify_exp": True, "require": ["exp", "iat", "userId", "role"]},
        )

        required_fields = ["userId", "role"]
        for field in required_fields:
            if not payload.get(field):
                raise TokenInvalidError()
        return payload

    except jwt.ExpiredSignatureError:
        raise TokenExpiredError()
    except jwt.InvalidTokenError as e:
        raise TokenInvalidError()
    except Exception as e:
        raise TokenInvalidError()
