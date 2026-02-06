"""Legacy peer service - re-exports from ipsec_peer_service.

This module exists for backward compatibility. New code should import
from backend.app.services.ipsec_peer_service directly.
"""

from backend.app.services.ipsec_peer_service import (  # noqa: F401
    create_peer,
    get_all_peers,
    get_decrypted_psk,
    get_peer_by_id,
    get_peer_by_name,
    update_peer,
    validate_peer_config,
)
