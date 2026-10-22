"""Role-Based Access Control (RBAC) Architecture for JARVIS Ecosystem.

Three-tier privilege hierarchy:
    USER < ADMIN < SUPERADMIN

Rules:
- SUPERADMIN is configured via environment (BOT_OWNER_ID, SUPERADMIN_ID, or SUPER_ADMINS).
  SUPERADMIN privileges are supreme, immutable, and cannot be revoked by anyone.
- Only SUPERADMIN has permissions to promote standard users to ADMIN or demote ADMIN to USER.
- Only SUPERADMIN has permission to orchestrate via CLI administration (./Jarvis -a).
- In-chat moderation commands (/ban, /unban, /mute, /unmute, /user, /broadcast) are available
  to both ADMIN and SUPERADMIN.
- ADMINs cannot ban, mute, or demote fellow ADMINs or SUPERADMINs.
"""

from enum import Enum
from typing import Optional
from src.config import SUPERADMINS, BOT_OWNER_ID

class Role(str, Enum):
    USER = "USER"
    ADMIN = "ADMIN"
    SUPERADMIN = "SUPERADMIN"

    @property
    def rank(self) -> int:
        order = {
            self.USER.value: 1,
            self.ADMIN.value: 2,
            self.SUPERADMIN.value: 3,
        }
        return order.get(self.value, 1)

    def __lt__(self, other: object) -> bool:
        if isinstance(other, Role):
            return self.rank < other.rank
        return NotImplemented

    def __le__(self, other: object) -> bool:
        if isinstance(other, Role):
            return self.rank <= other.rank
        return NotImplemented

    def __gt__(self, other: object) -> bool:
        if isinstance(other, Role):
            return self.rank > other.rank
        return NotImplemented

    def __ge__(self, other: object) -> bool:
        if isinstance(other, Role):
            return self.rank >= other.rank
        return NotImplemented

    def __str__(self) -> str:
        return self.value

def is_superadmin(user_id: int | str | None) -> bool:
    """Check if the given Telegram user ID is a configured Superadmin."""
    if user_id is None:
        return False
    try:
        uid = int(user_id)
    except (ValueError, TypeError):
        return False

    return uid in SUPERADMINS

def resolve_user_role(
    user_id: int | str,
    db_role: Optional[str] = None,
    is_admin: bool = False,
) -> Role:
    """Resolve the effective role of a user given their ID, DB role, and DB is_admin flag."""
    if is_superadmin(user_id):
        return Role.SUPERADMIN
    if db_role and db_role.upper() == Role.SUPERADMIN.value:
        return Role.SUPERADMIN
    if (db_role and db_role.upper() == Role.ADMIN.value) or is_admin:
        return Role.ADMIN
    return Role.USER

def can_moderate(actor_role: Role) -> bool:
    """Check if role can execute in-chat moderation commands (/ban, /unban, /mute, etc.)."""
    return actor_role >= Role.ADMIN

def can_govern(actor_role: Role) -> bool:
    """Check if role can execute governance commands (/promote, /demote, /maintenance)."""
    return actor_role == Role.SUPERADMIN

def can_manage_cli(actor_role: Role) -> bool:
    """Check if role has rights to access CLI administration (./Jarvis -a)."""
    return actor_role == Role.SUPERADMIN

def can_promote_or_demote(actor_role: Role) -> bool:
    """Check if role has authority to promote/demote users."""
    return actor_role == Role.SUPERADMIN

def can_target_user(actor_role: Role, target_role: Role) -> bool:
    """
    Enforce target hierarchy rules:
    - Nobody can target a SUPERADMIN (supreme & immutable).
    - SUPERADMIN can target anyone with lower rank (ADMIN and USER).
    - ADMIN can ONLY target standard USERs (cannot target other ADMINs or SUPERADMIN).
    - USER cannot target anyone.
    """
    if target_role == Role.SUPERADMIN:
        return False
    if actor_role == Role.SUPERADMIN:
        return True
    if actor_role == Role.ADMIN:
        return target_role < Role.ADMIN
    return False

def verify_cli_superadmin(caller_id: int | str | None = None) -> bool:
    """
    Verify Superadmin authorization for CLI operations.
    If caller_id is provided, checks that it matches a configured superadmin.
    If caller_id is None, verifies that at least one Superadmin / Bot Owner is configured in env.
    """
    if not SUPERADMINS and BOT_OWNER_ID is None:
        return False
    if caller_id is not None:
        return is_superadmin(caller_id)
    return True
