<#
.SYNOPSIS
  One-command release for nano-empire-tollbooth.
  Rebuild -> validate -> upload to PyPI -> smoke-test from PyPI -> git tag.

.DESCRIPTION
  Credentials are NEVER passed on the command line or stored in the repo.
  twine reads them automatically from one of:
    1. %USERPROFILE%\.pypirc   (recommended — see RELEASE.md)
    2. $env:TWINE_USERNAME / $env:TWINE_PASSWORD
  If neither is present the script stops BEFORE upload with instructions,
  so it never hangs on an interactive auth prompt.

.EXAMPLE
  .\release.ps1            # version read from pyproject.toml
  .\release.ps1 0.3.1      # explicit version
#>
param([string]$Version)

$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

function Step($m) { Write-Host "`n=== $m ===" -ForegroundColor Cyan }

# --- Resolve version from pyproject.toml if not supplied -------------------
if (-not $Version) {
  $line = Select-String -Path pyproject.toml -Pattern '^version\s*=\s*"([^"]+)"' | Select-Object -First 1
  if (-not $line) { throw "Could not read version from pyproject.toml" }
  $Version = $line.Matches[0].Groups[1].Value
}
$pkg = "nano-empire-tollbooth"
$mod = "nano_empire_tollbooth"
Write-Host "Releasing $pkg $Version" -ForegroundColor Green

# --- Credential preflight (fail fast, no hang) -----------------------------
$hasPypirc = Test-Path (Join-Path $env:USERPROFILE ".pypirc")
$hasEnv    = $env:TWINE_PASSWORD -and $env:TWINE_USERNAME
if (-not ($hasPypirc -or $hasEnv)) {
  Write-Host "`nNo PyPI credentials found." -ForegroundColor Yellow
  Write-Host "Create %USERPROFILE%\.pypirc once (see RELEASE.md), then re-run." -ForegroundColor Yellow
  Write-Host "The token stays in that file — it is never typed here or committed." -ForegroundColor Yellow
  exit 1
}

# --- Clean rebuild so artifacts always match source ------------------------
Step "Rebuild"
if (Test-Path dist) { Remove-Item dist\* -Force -ErrorAction SilentlyContinue }
python -m build
if ($LASTEXITCODE) { throw "build failed" }

Step "Validate metadata"
python -m twine check dist\*
if ($LASTEXITCODE) { throw "twine check failed" }

# --- Upload (idempotent: skips files already on PyPI) ----------------------
Step "Upload to PyPI"
python -m twine upload --skip-existing dist\*
if ($LASTEXITCODE) { throw "twine upload failed" }

# --- Smoke test from the live index ----------------------------------------
Step "Smoke test from PyPI"
$venv = Join-Path $env:TEMP "tollbooth-smoke-$Version"
if (Test-Path $venv) { Remove-Item $venv -Recurse -Force }
python -m venv $venv
$py = Join-Path $venv "Scripts\python.exe"
$ok = $false
foreach ($attempt in 1..10) {
  & $py -m pip install --quiet --no-cache-dir "$pkg==$Version" 2>$null
  if ($LASTEXITCODE -eq 0) { $ok = $true; break }
  Write-Host "  index not propagated yet (attempt $attempt/10) — waiting 15s..."
  Start-Sleep -Seconds 15
}
if (-not $ok) { throw "Could not install $pkg==$Version from PyPI after retries" }
$installed = & $py -c "import $mod as t; print(t.__version__)"
Write-Host "  installed version: $installed"
if ($installed.Trim() -ne $Version) { throw "Version mismatch: PyPI has $installed, expected $Version" }
& (Join-Path $venv "Scripts\tollbooth.exe") status
Remove-Item $venv -Recurse -Force -ErrorAction SilentlyContinue

# --- Tag the released commit (push is left to you) -------------------------
Step "Tag"
$tag = "v$Version"
if (git rev-parse $tag 2>$null) {
  Write-Host "  tag $tag already exists"
} else {
  git tag -a $tag -m "$pkg $Version"
  Write-Host "  created tag $tag  (push with: git push origin $tag)"
}

Write-Host "`nDONE — $pkg $Version is live on https://pypi.org/project/$pkg/$Version/" -ForegroundColor Green
