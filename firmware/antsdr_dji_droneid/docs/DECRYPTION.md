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

5) LOCAL handling AFTER server decrypt (no second crypto)
---------------------------------------------------------
Once the cloud returns plaintext JSON, everything else is local cache + format.

E200 (process_encrypte.cpp) after HTTP 200:
  1. Parse JSON fields (from firmware string table next to dji_O,4 format):
       sn, model, lon, lat, alt, height, gps_time, uuid,
       pilot_lon, pilot_lat, home_lon, home_lat, yaw, hash
  2. Cache by packet hash (CacheHttpData):
       "Cache secrect hit [SN: {}]"
       "Cached new data [TTL: {}min]"
       "Cache data packet hit/not hit"
     → later detections reuse SN/GPS without re-calling the server until TTL expires
  3. Emit plaintext CSV (same TCP/UDP path as O2/O3):
       dji_O,4,<freq>,<rssi>,dji(<hash>),<SN>,<lon>,<lat>,...

Host (dji_receiver.py) — local only, no decrypt:
  if protocol == "4" and field5 (serial) length >= 5:
      device_type = "DJI O4 (Decrypted)"   # already plaintext from E200
  else:
      device_type = "DJI Encrypted (O4)"   # hash-only fallback

There is NO local O4 crypto algorithm in public code. Local steps are:
  JSON parse → in-memory cache → CSV → ZMQ JSON.

6) How to enable O4 decrypt (if you have a license)
---------------------------------------------------
1. Place dragonscope.cfg next to dragonscope.py (remote URL + license_key)
2. Run: python3 dragonscope.py   (port 80)
3. On E200: fw_setenv api_host <PC-IP> ; fw_setenv request_time 1 ; reboot
4. O4 drone with motors spinning
5. Expect dragonscope log: INFP: <serial> lat=... lon=...
   and dji_O,4 lines with non-empty serial field

7) Internet research: "decrypt once online, then locally forever?"
-----------------------------------------------------------------
Public sources (as of 2026):

  Official / vendor
  - DragonScope product page: "Active internet connectivity required for
    OcuSync 4 telemetry"; without internet → hash-level detection only.
    https://cemaxecuter.com/?product=dragonscope-drone-id-service
  - antsdr_dji_droneid / dragonsdr_dji_droneid README: O4 position needs
    DragonScope; O2/O3 stay fully offline.
  - dragonscope.py: every decrypt is a remote HTTP call; no local cipher.

  Open-source community
  - proto17/dji_droneid #50, #60: O3+/O4 described as strongly encrypted;
    open tools can demodulate/CRC but not recover SN/GPS; paid decrypt
    rumored, no public algorithm published.
  - antsdr_dji_droneid #20: encrypted O4 cannot be decoded on the module
    alone; raw analysis needs other SDR tooling (e.g. GR-droneid), still
    without a public O4 decrypt key.

What DOES exist locally after one successful online decrypt
  A) E200 firmware TTL cache (minutes, same flight/session)
     - "Cache secrect hit [SN: {}]" / "Cached new data [TTL: {}min]"
     - Reuses SN/GPS for the same packet hash without re-calling cloud
     - Expires; not a permanent offline decrypt capability

  B) Session hash correlation (not decrypt)
     - Hash ID (e.g. drone-alert-9dc89f97) is stable for a flight/session
     - You can map hash → serial yourself AFTER online decrypt once,
       then label later detections of the SAME hash without crypto
     - New flight / new session → new hash → need online decrypt again
       for SN/GPS (GPS also changes every packet)

  C) No public method to turn one cloud plaintext into a local O4 cipher
     that decrypts future encrypted hex offline.

Practical local reuse (legitimate ops, after you already have online SN):
  1. When dragonscope prints INFP/CRYP, save: hash, sn, timestamp
  2. On later dji_O,4 lines with empty serial, if field4 hash matches,
     attach the saved serial locally in your own logger/UI
  3. Live GPS/alt/speed for O4 still need fresh online decrypt (or E200
     cache while TTL is valid) — one old plaintext does not unlock new hex
