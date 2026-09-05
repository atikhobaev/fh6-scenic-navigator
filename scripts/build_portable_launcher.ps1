param([string]$Output = '.worktrees/release/FH6_Scenic_Navigator_v1.20.0_Windows_x64.exe', [Parameter(Mandatory=$true)][string]$PythonEmbedZip, [string]$Python = 'python', [string]$Go = 'go')
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$Output = [IO.Path]::GetFullPath($Output)
$PythonEmbedZip = (Resolve-Path -LiteralPath $PythonEmbedZip).Path
Set-Location $root
$expected = '7d2650fd9d1b9d002d4a315d5f354247fd6a44f30517c7ef577b08f57a0fb6d9'
if ((Get-FileHash -LiteralPath $PythonEmbedZip -Algorithm SHA256).Hash.ToLowerInvariant() -ne $expected) { throw 'CPython archive SHA-256 mismatch' }
$asset = Join-Path $root 'launcher_native/assets/python_embed.zip'
$oldRuntime = [IO.File]::ReadAllBytes($asset)
$oldVerify = $env:FH6_RELEASE_VERIFY
$oldCgo = $env:CGO_ENABLED
$oldGoos = $env:GOOS
$oldGoarch = $env:GOARCH
try {
    Copy-Item -LiteralPath $PythonEmbedZip -Destination $asset -Force
    & $Python -X utf8 scripts/build_launcher_payload.py --version 1.20.0
    if ($LASTEXITCODE -ne 0) { throw 'Payload build failed' }
    $env:FH6_RELEASE_VERIFY = '1'
    & $Go test ./...
    if ($LASTEXITCODE -ne 0) { throw 'Go release tests failed' }
    $env:CGO_ENABLED = '0'; $env:GOOS = 'windows'; $env:GOARCH = 'amd64'
    New-Item -ItemType Directory -Force (Split-Path $Output -Parent) | Out-Null
    & $Go build -buildvcs=false -trimpath '-ldflags=-H=windowsgui -s -w' -o $Output ./cmd/fh6-launcher
    if ($LASTEXITCODE -ne 0) { throw 'Windows build failed' }
    & $Python -X utf8 scripts/validate_portable_exe.py $Output
    if ($LASTEXITCODE -ne 0) { throw 'Portable validation failed' }
    $hash = (Get-FileHash -LiteralPath $Output -Algorithm SHA256).Hash.ToLowerInvariant()
    "$hash  $(Split-Path $Output -Leaf)" | Set-Content -LiteralPath "$Output.sha256" -Encoding ascii
    $stable = Join-Path (Split-Path $Output -Parent) 'FH6_Scenic_Navigator_Windows_x64.exe'
    if ([IO.Path]::GetFullPath($Output) -ne [IO.Path]::GetFullPath($stable)) { Copy-Item -LiteralPath $Output -Destination $stable -Force }
    "$hash  FH6_Scenic_Navigator_Windows_x64.exe" | Set-Content -LiteralPath "$stable.sha256" -Encoding ascii
    if ((Get-FileHash $stable -Algorithm SHA256).Hash.ToLowerInvariant() -ne $hash) { throw 'Stable alias mismatch' }
} finally {
    [IO.File]::WriteAllBytes($asset, $oldRuntime)
    $env:FH6_RELEASE_VERIFY=$oldVerify; $env:CGO_ENABLED=$oldCgo; $env:GOOS=$oldGoos; $env:GOARCH=$oldGoarch
}
