# Run PowerShell as Administrator only if Windows Firewall blocks the phone/Forza.
$ErrorActionPreference = 'Stop'
$rules = @(
  @{ Name='FH6 Scenic Navigator HTTP'; Protocol='TCP'; Port=8080 },
  @{ Name='FH6 Scenic Navigator Telemetry'; Protocol='UDP'; Port=1234 }
)
foreach ($r in $rules) {
  Get-NetFirewallRule -DisplayName $r.Name -ErrorAction SilentlyContinue | Remove-NetFirewallRule -ErrorAction SilentlyContinue
  New-NetFirewallRule -DisplayName $r.Name -Direction Inbound -Action Allow -Protocol $r.Protocol -LocalPort $r.Port -Profile Private | Out-Null
  Write-Host "Allowed $($r.Protocol) port $($r.Port)" -ForegroundColor Green
}
Write-Host 'Done. Rules are limited to the Private network profile.' -ForegroundColor Cyan
