#!/usr/bin/env python3
"""Probe for AntSDR E200 on network and auto-configure when found."""
import socket
import subprocess
import sys
import time

CANDIDATE_HOSTS = [
    "192.168.1.10", "172.31.100.2",
] + [f"192.168.1.{i}" for i in range(1, 254)]

E200_CONFIG = """fw_setenv ipaddr_eth {e200_ip}
fw_setenv tcp_serverip {pc_ip}
fw_setenv tcp_serverport 52002
fw_setenv gain_mode fast_attack
fw_setenv heart_beate_time 30
fw_setenv api_host {pc_ip}
fw_setenv request_time 1
fw_setenv auth_secret placeholder
fw_setenv token_secret placeholder
fw_setenv device_serial antsdr_e200
fw_setenv device_mode auto
"""


def local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except OSError:
        return None


def ping(ip, timeout=0.5):
    try:
        r = subprocess.run(
            ["ping", "-c", "1", "-W", str(int(timeout)), ip],
            capture_output=True, timeout=timeout + 1,
        )
        return r.returncode == 0
    except Exception:
        return False


def ssh_check(ip, password):
    for pw in [password, "1", "abawavearm", "analog"]:
        try:
            r = subprocess.run(
                [
                    "sshpass", "-p", pw,
                    "ssh", "-o", "StrictHostKeyChecking=no",
                    "-o", "UserKnownHostsFile=/dev/null",
                    "-o", "ConnectTimeout=3",
                    f"root@{ip}", "ps | grep -E 'drone_dji_rid_decode|done_dji_release' | grep -v grep",
                ],
                capture_output=True, text=True, timeout=8,
            )
            if r.returncode == 0 and r.stdout.strip():
                return pw, r.stdout.strip()
        except Exception:
            pass
    return None, None


def ssh_config(ip, password, pc_ip, e200_ip):
    script = E200_CONFIG.format(pc_ip=pc_ip, e200_ip=e200_ip)
    cmds = script.strip().split("\n") + ["reboot"]
    joined = "; ".join(cmds)
    subprocess.run(
        [
            "sshpass", "-p", password,
            "ssh", "-o", "StrictHostKeyChecking=no",
            "-o", "UserKnownHostsFile=/dev/null",
            "-o", "ConnectTimeout=5",
            f"root@{ip}", joined,
        ],
        timeout=15,
    )


def main():
    pc_ip = local_ip()
    print(f"Auto-probe started. PC IP: {pc_ip}")
    print("Scanning for AntSDR E200...")

    found = set()
    while True:
        for ip in CANDIDATE_HOSTS:
            if ip in found:
                continue
            if not ping(ip):
                continue
            print(f"  Host up: {ip}")
            pw, procs = ssh_check(ip, "1")
            if procs:
                print(f"  AntSDR @ {ip}: {procs}")
                found.add(ip)
                if "drone_dji_rid_decode" in procs and pc_ip:
                    print(f"  Configuring api_host={pc_ip} ...")
                    ssh_config(ip, pw, pc_ip, ip)
                    print("  Reboot sent. E200 should send hex to this machine.")
        time.sleep(10)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
