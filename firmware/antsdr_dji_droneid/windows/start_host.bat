@echo off
REM AntSDR E200 O4 host-side tools (run on your Windows PC)
REM Requires: Python 3, Ethernet to E200 (192.168.1.x)

cd /d "%~dp0.."

echo.
echo === AntSDR O4 Host Setup ===
echo.
echo Your PC must be on the same subnet as the E200 (usually 192.168.1.x).
echo Find your PC IP with: ipconfig
echo.
echo E200 serial console is COM7 (115200) - use PuTTY or this terminal only for fw_setenv.
echo Encrypted hex arrives over ETHERNET to port 80, not over COM7.
echo.

set /p PC_IP="Enter your PC Ethernet IP (e.g. 192.168.1.9): "
if "%PC_IP%"=="" (
    echo No IP entered, exiting.
    exit /b 1
)

echo.
echo Configure E200 over COM7 serial (login root / 1), then run:
echo   fw_setenv ipaddr_eth 192.168.1.10
echo   fw_setenv tcp_serverip %PC_IP%
echo   fw_setenv tcp_serverport 52002
echo   fw_setenv api_host %PC_IP%
echo   fw_setenv request_time 1
echo   fw_setenv gain_mode fast_attack
echo   fw_setenv device_mode auto
echo   reboot
echo.
pause

echo Starting hex logger on port 80 (needs Admin if port 80 blocked)...
start "O4 Hex Logger" cmd /k python hex_logger.py

timeout /t 2 /nobreak >nul

echo Starting dji_receiver (new firmware mode, port 52002)...
start "DJI Receiver" cmd /k python dji_receiver.py -d --mode new --listen-port 52002

echo.
echo Two windows opened. Power on an O4 drone with motors spinning to test.
echo Hex log file: o4_encrypted_hex.log
echo.
pause
