import os
import shutil
import socket
import subprocess
import sys
import textwrap
import time

import pytest

from backend.daemon.ops.nftables import apply_isolation_rules

PT_NAMESPACE = "ns_pt"
PT_HOST_NAMESPACE = "pt-host"
CT_HOST_NAMESPACE = "ct-host"
PT_IP = "10.0.0.1"
PT_HOST_IP = "10.0.0.2"
CT_IP = "10.0.1.1"
CT_HOST_IP = "10.0.1.2"


def _require_privileged_tools() -> None:
    if os.geteuid() != 0:
        pytest.skip("requires root privileges for netns and raw sockets")
    for tool in ("ip", "nft", "sysctl"):
        if shutil.which(tool) is None:
            pytest.skip(f"missing required tool: {tool}")


def _run(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, check=True, text=True, **kwargs)


def _run_best_effort(cmd: list[str]) -> None:
    subprocess.run(cmd, check=False, text=True)


def _netns_exec(namespace: str, args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
    return _run(["ip", "netns", "exec", namespace, *args], **kwargs)


def _netns_popen(namespace: str, args: list[str]) -> subprocess.Popen[str]:
    return subprocess.Popen(["ip", "netns", "exec", namespace, *args], text=True)


def _udp_receiver_code(port: int, expect_receive: bool, timeout: float) -> str:
    if expect_receive:
        on_timeout = "sys.exit(1)"
        on_receive = "sys.exit(0)"
    else:
        on_timeout = "sys.exit(0)"
        on_receive = "sys.exit(1)"
    return textwrap.dedent(
        f"""
        import socket
        import sys

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(("{CT_HOST_IP}", {port}))
        sock.settimeout({timeout})
        try:
            sock.recvfrom(4096)
            {on_receive}
        except socket.timeout:
            {on_timeout}
        """
    ).strip()


def _udp_send_code(port: int) -> str:
    return textwrap.dedent(
        f"""
        import socket

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.sendto(b"ping", ("{CT_HOST_IP}", {port}))
        """
    ).strip()


def _esp_receiver_code(timeout: float) -> str:
    return textwrap.dedent(
        f"""
        import socket
        import sys

        sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ESP)
        sock.bind(("{CT_HOST_IP}", 0))
        sock.settimeout({timeout})
        try:
            sock.recv(4096)
            sys.exit(0)
        except socket.timeout:
            sys.exit(1)
        """
    ).strip()


def _esp_sender_code() -> str:
    return textwrap.dedent(
        f"""
        import socket
        import struct

        def checksum(data: bytes) -> int:
            if len(data) % 2:
                data += b"\\x00"
            total = 0
            for i in range(0, len(data), 2):
                total += (data[i] << 8) + data[i + 1]
            while total > 0xFFFF:
                total = (total & 0xFFFF) + (total >> 16)
            return (~total) & 0xFFFF

        src_ip = "{PT_HOST_IP}"
        dst_ip = "{CT_HOST_IP}"
        payload = b"ESPTEST"
        version_ihl = (4 << 4) | 5
        total_len = 20 + len(payload)
        header = struct.pack(
            "!BBHHHBBH4s4s",
            version_ihl,
            0,
            total_len,
            0,
            0,
            64,
            socket.IPPROTO_ESP,
            0,
            socket.inet_aton(src_ip),
            socket.inet_aton(dst_ip),
        )
        checksum_value = checksum(header)
        header = struct.pack(
            "!BBHHHBBH4s4s",
            version_ihl,
            0,
            total_len,
            0,
            0,
            64,
            socket.IPPROTO_ESP,
            checksum_value,
            socket.inet_aton(src_ip),
            socket.inet_aton(dst_ip),
        )
        packet = header + payload
        sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_RAW)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)
        sock.sendto(packet, (dst_ip, 0))
        """
    ).strip()


def _run_udp_check(port: int, expect_receive: bool) -> None:
    receiver = _netns_popen(
        CT_HOST_NAMESPACE, [sys.executable, "-c", _udp_receiver_code(port, expect_receive, 1.5)]
    )
    time.sleep(0.2)
    _netns_exec(PT_HOST_NAMESPACE, [sys.executable, "-c", _udp_send_code(port)])
    receiver.wait(timeout=3)
    assert receiver.returncode == 0


def _run_esp_check() -> None:
    receiver = _netns_popen(
        CT_HOST_NAMESPACE, [sys.executable, "-c", _esp_receiver_code(1.5)]
    )
    time.sleep(0.2)
    _netns_exec(PT_HOST_NAMESPACE, [sys.executable, "-c", _esp_sender_code()])
    receiver.wait(timeout=3)
    assert receiver.returncode == 0


def test_isolation_rules_enforce_packet_flow_between_pt_ct() -> None:
    _require_privileged_tools()
    namespaces = (PT_NAMESPACE, PT_HOST_NAMESPACE, CT_HOST_NAMESPACE)

    for namespace in namespaces:
        _run_best_effort(["ip", "netns", "del", namespace])

    try:
        for namespace in namespaces:
            _run(["ip", "netns", "add", namespace])

        _run(["ip", "link", "add", "pt", "type", "veth", "peer", "name", "pt-host"])
        _run(["ip", "link", "set", "pt", "netns", PT_NAMESPACE])
        _run(["ip", "link", "set", "pt-host", "netns", PT_HOST_NAMESPACE])

        _run(["ip", "link", "add", "ct", "type", "veth", "peer", "name", "ct-host"])
        _run(["ip", "link", "set", "ct", "netns", PT_NAMESPACE])
        _run(["ip", "link", "set", "ct-host", "netns", CT_HOST_NAMESPACE])

        _netns_exec(PT_NAMESPACE, ["ip", "addr", "add", f"{PT_IP}/24", "dev", "pt"])
        _netns_exec(PT_NAMESPACE, ["ip", "addr", "add", f"{CT_IP}/24", "dev", "ct"])
        _netns_exec(PT_NAMESPACE, ["ip", "link", "set", "pt", "up"])
        _netns_exec(PT_NAMESPACE, ["ip", "link", "set", "ct", "up"])
        _netns_exec(PT_NAMESPACE, ["ip", "link", "set", "lo", "up"])
        _netns_exec(PT_NAMESPACE, ["sysctl", "-w", "net.ipv4.ip_forward=1"])

        _netns_exec(PT_HOST_NAMESPACE, ["ip", "addr", "add", f"{PT_HOST_IP}/24", "dev", "pt-host"])
        _netns_exec(PT_HOST_NAMESPACE, ["ip", "link", "set", "pt-host", "up"])
        _netns_exec(PT_HOST_NAMESPACE, ["ip", "link", "set", "lo", "up"])
        _netns_exec(PT_HOST_NAMESPACE, ["ip", "route", "add", "default", "via", PT_IP])

        _netns_exec(CT_HOST_NAMESPACE, ["ip", "addr", "add", f"{CT_HOST_IP}/24", "dev", "ct-host"])
        _netns_exec(CT_HOST_NAMESPACE, ["ip", "link", "set", "ct-host", "up"])
        _netns_exec(CT_HOST_NAMESPACE, ["ip", "link", "set", "lo", "up"])
        _netns_exec(CT_HOST_NAMESPACE, ["ip", "route", "add", "default", "via", CT_IP])

        apply_isolation_rules(namespaces=[PT_NAMESPACE], allowed_ifnames=["pt", "ct"])

        _run_udp_check(500, expect_receive=True)
        _run_udp_check(4500, expect_receive=True)
        _run_udp_check(9999, expect_receive=False)
        _run_esp_check()
    finally:
        for namespace in namespaces:
            _run_best_effort(["ip", "netns", "del", namespace])
