# O4 hex capture — run as Administrator (port 80)
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

$pcIp = (Get-NetIPAddress -AddressFamily IPv4 |
    Where-Object { $_.InterfaceAlias -notmatch 'Loopback' -and $_.IPAddress -notmatch '^169\.' } |
    Select-Object -First 1 -ExpandProperty IPAddress)

if (-not $pcIp) { $pcIp = Read-Host "Enter your PC Ethernet IP" }

Write-Host "`n=== O4 Hex Capture ===" -ForegroundColor Cyan
Write-Host "PC IP (set api_host to this): $pcIp"
Write-Host "Log file: o4_encrypted_hex.log`n"

Write-Host "=== Paste on E200 COM7 (115200, root/analog) ===" -ForegroundColor Yellow
@"
fw_setenv ipaddr_eth 192.168.1.10
fw_setenv tcp_serverip $pcIp
fw_setenv tcp_serverport 52002
fw_setenv gain_mode fast_attack
fw_setenv heart_beate_time 30
fw_setenv api_host $pcIp
fw_setenv request_time 1
fw_setenv auth_secret placeholder
fw_setenv token_secret placeholder
fw_setenv device_serial antsdr_e200
fw_setenv device_mode auto
reboot
"@

# Firewall rules
foreach ($port in 80, 52002) {
    $rule = "AntSDR-O4-Port-$port"
    if (-not (Get-NetFirewallRule -DisplayName $rule -ErrorAction SilentlyContinue)) {
        New-NetFirewallRule -DisplayName $rule -Direction Inbound -Action Allow -Protocol TCP -LocalPort $port | Out-Null
        Write-Host "Firewall: allowed TCP $port"
    }
}

Write-Host "`nStarting capture (self-test + monitor)..." -ForegroundColor Green
python run_capture.py --self-test

if (Test-Path "o4_encrypted_hex.log") {
    Write-Host "`n=== Captured hex ===" -ForegroundColor Cyan
    Get-Content "o4_encrypted_hex.log" -Tail 5
}
