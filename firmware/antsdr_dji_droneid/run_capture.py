#!/usr/bin/env python3
"""
Start O4 hex capture + dji_receiver and monitor for encrypted hex.

Usage:
  python3 run_capture.py                    # port 80 (needs root/admin on some OS)
  python3 run_capture.py --port 8080        # alternate port (E200 firmware uses 80 only)
  python3 run_capture.py --self-test        # verify pipeline without E200
  python3 run_capture.py --find             # print hex from log and exit
"""
import argparse
import os
import socket
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
LOG_FILE = SCRIPT_DIR / "o4_encrypted_hex.log"


def local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except OSError:
        return "127.0.0.1"


def print_e200_config(pc_ip: str):
    print("\n=== Paste on E200 COM7 (root/analog) ===\n")
    print(f"""fw_setenv ipaddr_eth 192.168.1.10
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
reboot""")
    print("\n=== End config ===\n")


def find_hex():
    if not LOG_FILE.exists():
        print(f"No log yet: {LOG_FILE}")
        return 1
    lines = LOG_FILE.read_text().strip().splitlines()
    if not lines:
        print(f"Log empty: {LOG_FILE}")
        return 1
    print(f"Found {len(lines)} hex capture(s) in {LOG_FILE}:\n")
    for i, line in enumerate(lines[-10:], 1):
        line = line.strip()
        if len(line) >= 20 and line[10] == " " and line[13] == ":":
            ts, hx = line[:19], line[20:]
            print(f"[{i}] {ts}  len={len(hx)}  {hx[:80]}{'...' if len(hx) > 80 else ''}")
        else:
            print(f"[{i}] {line[:100]}")
    latest_line = lines[-1].strip()
    latest = latest_line[20:] if len(latest_line) > 20 else latest_line
    out = SCRIPT_DIR / "latest_o4_hex.txt"
    out.write_text(latest + "\n")
    print(f"\nLatest hex saved to: {out}")
    return 0


def self_test(port: int):
    sample = (
        "a1b2c3d4e5f6789012345678901234567890abcdef"
        "0123456789abcdef0123456789abcdef0123456789abcdef"
        "deadbeefcafebabe0123456789abcdef0123456789abcdef"
    )
    url = f"http://127.0.0.1:{port}/api/o4online/decrypt?hex={sample}"
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            body = resp.read()
        print(f"Self-test OK: HTTP {resp.status} {body.decode()}")
        time.sleep(0.3)
        return find_hex()
    except Exception as e:
        print(f"Self-test FAILED: {e}")
        return 1


def tail_log(stop_event: threading.Event):
    last_size = LOG_FILE.stat().st_size if LOG_FILE.exists() else 0
    while not stop_event.is_set():
        if LOG_FILE.exists():
            size = LOG_FILE.stat().st_size
            if size > last_size:
                with open(LOG_FILE) as f:
                    f.seek(last_size)
                    new = f.read()
                    if new.strip():
                        print(new, end="", flush=True)
                last_size = size
        stop_event.wait(0.5)


def main():
    parser = argparse.ArgumentParser(description="O4 hex capture orchestrator")
    parser.add_argument("--port", type=int, default=int(os.environ.get("HEX_LOGGER_PORT", "80")))
    parser.add_argument("--self-test", action="store_true", help="Send test hex after startup")
    parser.add_argument("--find", action="store_true", help="Print captured hex from log")
    parser.add_argument("--no-receiver", action="store_true", help="Skip dji_receiver.py")
    args = parser.parse_args()

    if args.find:
        sys.exit(find_hex())

    pc_ip = local_ip()
    env = os.environ.copy()
    env["HEX_LOGGER_PORT"] = str(args.port)

    print("O4 Capture — starting services")
    print(f"  PC IP (use for api_host): {pc_ip}")
    print(f"  Hex logger port:          {args.port}")
    print(f"  Log file:                 {LOG_FILE}")
    print_e200_config(pc_ip)

    hex_proc = subprocess.Popen(
        [sys.executable, str(SCRIPT_DIR / "hex_logger.py")],
        env=env,
        cwd=str(SCRIPT_DIR),
    )
    recv_proc = None
    if not args.no_receiver:
        recv_proc = subprocess.Popen(
            [sys.executable, str(SCRIPT_DIR / "dji_receiver.py"), "-d", "--mode", "new", "--listen-port", "52002"],
            cwd=str(SCRIPT_DIR),
        )

    time.sleep(1)
    if hex_proc.poll() is not None:
        print("ERROR: hex_logger failed to start (port 80 may need admin). Try: --port 8080")
        sys.exit(1)

    stop = threading.Event()
    tail = threading.Thread(target=tail_log, args=(stop,), daemon=True)
    tail.start()

    if args.self_test:
        time.sleep(0.5)
        rc = self_test(args.port)
        if rc != 0:
            hex_proc.terminate()
            if recv_proc:
                recv_proc.terminate()
            sys.exit(rc)
        print("\nPipeline verified. Waiting for real E200 hex (Ctrl+C to stop)...")

    print("Listening for E200 → GET /api/o4online/decrypt?hex=...")
    print("Need: O4 drone, motors spinning, api_host set to your PC IP\n")

    try:
        while True:
            time.sleep(1)
            if hex_proc.poll() is not None:
                print("hex_logger exited unexpectedly")
                break
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        stop.set()
        hex_proc.terminate()
        if recv_proc:
            recv_proc.terminate()
        find_hex()


if __name__ == "__main__":
    main()
