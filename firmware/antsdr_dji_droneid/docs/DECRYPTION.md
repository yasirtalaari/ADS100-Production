O4 / O2-O3 Decryption Map
=========================
Source: antsdr_dji_droneid O4 firmware (drone_dji_rid_decode) + dragonscope.py

1) O2 / O3 — LOCAL DECODE (no license)
--------------------------------------
Where:  /sbin/drone_dji_rid_decode on E200 (DroneIDProcess.cpp)
What:   Full offline demod + decode
Output: dji_O,2/3,<freq>,<rssi>,<model>(<type>),<SERIAL>,lat,lon,...
Your COM7 log (Mavic Air 2) is this path — serial already decrypted on-device.

2) O4 — ONLINE DECRYPT ONLY (licensed cloud)
--------------------------------------------
Where decryption actually happens: NOT in public firmware, NOT in dragonscope.py.

Flow:
  E200 RF → processEncrypte (process_encrypte.cpp)
         → bin2hex(payload)
         → HTTP GET http://<api_host>/api/o4online/decrypt?hex=<payload>
         → parse JSON { sn, lat, lon, ... }
         → fill dji_O,4,... CSV with serial/GPS if reply has sn

Host proxy (dragonscope.py):
  Listens on :80 for the same path
  If no license_key → returns {"sn":""}  (detection only; hex can still be logged)
  If license_key set → forwards to remote:
       GET {remote}/api/o4online/decrypt?hex=...
       Headers: x-api-key, x-device-id, User-Agent: DragonScope/1.0
  Returns cloud JSON to E200

Config (dragonscope.cfg — provided with license, not public):
  {
    "remote": "https://CHANGE_ME",
    "license_key": "CHANGE_ME",
    "listen_port": 80,
    "listen_addr": "0.0.0.0"
  }

Commercial product: DragonScope Drone ID Service (annual subscription, internet required)
  https://cemaxecuter.com/?product=dragonscope-drone-id-service

3) What is NOT O4 DroneID decryption
------------------------------------
Found in firmware but used for HTTP/auth packaging, not O4 payload crypto:
  - xxtea_encrypt / encrypt_for_url / decrypt_for_url
  - my_secret_key_2026
  - auth_secret / token_secret env vars (required placeholders for firmware)

4) Without DragonScope license
------------------------------
O4 detection still works:
  dji_O,4,<freq>,<rssi>,dji(<hash>),,...
  → dji_receiver shows drone-alert-<hash>, freq, RSSI
Encrypted hex can be captured via hex_logger.py / dragonscope.py log
Full serial/GPS for O4 requires licensed remote decrypt + internet

5) How to enable O4 decrypt (if you have a license)
---------------------------------------------------
1. Place dragonscope.cfg next to dragonscope.py (remote URL + license_key)
2. Run: python3 dragonscope.py   (port 80)
3. On E200: fw_setenv api_host <PC-IP> ; fw_setenv request_time 1 ; reboot
4. O4 drone with motors spinning
5. Expect dragonscope log: INFP: <serial> lat=... lon=...
   and dji_O,4 lines with non-empty serial field
