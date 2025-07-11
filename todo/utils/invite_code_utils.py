import hashlib
import datetime


def generate_invite_code(team_name: str) -> str:
    """
    Generate a unique 6-character invite code for a team.

    Args:
        team_name: The name of the team

    Returns:
        A 6-character alphanumeric invite code
    """
    now = datetime.datetime.utcnow().isoformat()
    seed = f"{team_name}_{now}"

    hash_bytes = hashlib.sha256(seed.encode()).hexdigest()

    hash_int = int(hash_bytes[:10], 16)  # Take first 10 hex digits
    base36 = ""
    characters = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"

    while len(base36) < 6:
        hash_int, i = divmod(hash_int, 36) if hash_int > 0 else (0, 0)
        base36 = characters[i] + base36

        hash_int, i = divmod(hash_int, 36)
        base36 = characters[i] + base36

    return base36.zfill(6)
