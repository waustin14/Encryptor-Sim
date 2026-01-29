from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BOOT_TARGET_SECONDS = 30.0
BOOT_TIMESTAMP_DIR = "/var/run/encryptor"


def _read_boot_timestamp(filepath: str) -> float | None:
    """Read a boot timestamp from file.

    Args:
        filepath: Path to the timestamp file

    Returns:
        Unix timestamp as float, or None if file doesn't exist or is invalid
    """
    try:
        path = Path(filepath)
        if not path.exists():
            return None
        content = path.read_text().strip()
        if not content:
            return None
        return float(content)
    except (ValueError, OSError):
        return None


def _read_uptime_seconds() -> float | None:
    uptime_path = Path("/proc/uptime")
    if not uptime_path.exists():
        return None
    return float(uptime_path.read_text().split()[0])


def _get_system_boot_time() -> datetime:
    """Best-effort system boot time based on kernel uptime."""
    uptime_seconds = _read_uptime_seconds()
    if uptime_seconds is not None:
        return datetime.now(timezone.utc) - timedelta(seconds=uptime_seconds)
    return datetime.now(timezone.utc)


# Track system boot/startup time
_boot_start_time: datetime = _get_system_boot_time()


class Settings(BaseSettings):
    psk_encryption_key: str
    secret_key: str  # JWT signing key (REQUIRED - no default for security)
    database_url: str = "sqlite+pysqlite:///./app.db"
    daemon_socket_path: str = "/tmp/encryptor-sim-daemon.sock"

    model_config = SettingsConfigDict(env_prefix="APP_", env_file=".env")


@lru_cache
def get_settings() -> Settings:
    return Settings()


def get_boot_duration_seconds() -> float | None:
    """Get the boot duration from encryptor service timestamps.

    Boot duration is calculated from the time encryptor-namespaces started
    to when encryptor-api became ready. This measures actual service boot time,
    not system uptime.

    Returns:
        Boot duration in seconds (rounded to 1 decimal), or None if timestamps unavailable.
    """
    boot_start_path = f"{BOOT_TIMESTAMP_DIR}/boot-start"
    boot_complete_path = f"{BOOT_TIMESTAMP_DIR}/boot-complete"

    start_time = _read_boot_timestamp(boot_start_path)
    complete_time = _read_boot_timestamp(boot_complete_path)

    if start_time is None or complete_time is None:
        return None

    duration = complete_time - start_time
    return round(duration, 1)


def get_boot_start_time() -> datetime:
    """Get the system boot start time."""
    duration = get_boot_duration_seconds()
    if duration is None:
        return datetime.now(timezone.utc)
    return datetime.now(timezone.utc) - timedelta(seconds=duration)


settings = get_settings()
