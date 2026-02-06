$ErrorActionPreference = "Stop"

function Write-Section($text) {
  Write-Host ""
  Write-Host "== $text =="
}

function Read-SecretPlain($prompt) {
  $secure = Read-Host -Prompt $prompt -AsSecureString
  if (-not $secure) { return "" }
  $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
  try { return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr) }
  finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr) }
}

Write-Section "Overmind setup (Windows)"

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $repoRoot

Write-Section "Python virtual environment"
$pythonCmd = $null
try {
  & py -3 --version | Out-Null
  $pythonCmd = "py -3"
} catch {
  $pythonCmd = "python"
}

if (-not (Test-Path ".venv")) {
  Write-Host "Creating .venv..."
  & $pythonCmd -m venv .venv
}

Write-Host "Activating .venv..."
. .\.venv\Scripts\Activate.ps1

Write-Section "Install backend dependencies"
python -m pip install --upgrade pip
pip install -r requirements.txt

Write-Section "Build UI"
if (Test-Path "ui/package.json") {
  Push-Location ui
  if (Test-Path "package-lock.json") {
    npm ci
  } else {
    npm install
  }
  npm run build
  Pop-Location
}

Write-Section "Configure API keys"
$providers = @(
  "OPENAI_API_KEY",
  "ANTHROPIC_API_KEY",
  "GROQ_API_KEY",
  "GEMINI_API_KEY"
)

$setVars = @{}
foreach ($name in $providers) {
  $answer = Read-Host -Prompt "Set $name? (y/N)"
  if ($answer -match "^[Yy]") {
    $value = Read-SecretPlain "Enter $name"
    if ($value) {
      $env:$name = $value
      $setVars[$name] = $value
    }
  }
}

$persist = Read-Host -Prompt "Persist these variables for your user profile? (y/N)"
if ($persist -match "^[Yy]") {
  foreach ($kv in $setVars.GetEnumerator()) {
    setx $kv.Key $kv.Value | Out-Null
  }
  Write-Host "Saved. Restart your shell to pick up persisted variables."
}

Write-Section "Done"
Write-Host "To run:"
Write-Host "  .\\.venv\\Scripts\\Activate.ps1"
Write-Host "  python -m app --self"
