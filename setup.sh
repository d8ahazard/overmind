#!/usr/bin/env bash
set -euo pipefail

section() {
  echo ""
  echo "== $1 =="
}

section "Overmind setup (macOS/Linux)"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_ROOT"

section "Python virtual environment"
PYTHON_BIN="${PYTHON_BIN:-python3}"
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "python3 not found. Please install Python 3.10+."
  exit 1
fi

if [ ! -d ".venv" ]; then
  echo "Creating .venv..."
  "$PYTHON_BIN" -m venv .venv
fi

echo "Activating .venv..."
source .venv/bin/activate

section "Install backend dependencies"
python -m pip install --upgrade pip
pip install -r requirements.txt

section "Build UI"
if [ -f "ui/package.json" ]; then
  pushd ui >/dev/null
  if [ -f "package-lock.json" ]; then
    npm ci
  else
    npm install
  fi
  npm run build
  popd >/dev/null
fi

section "Configure API keys"
declare -a PROVIDERS=(
  "OPENAI_API_KEY"
  "ANTHROPIC_API_KEY"
  "GROQ_API_KEY"
  "GEMINI_API_KEY"
)

declare -A SET_VARS=()
for name in "${PROVIDERS[@]}"; do
  read -r -p "Set ${name}? (y/N) " answer
  if [[ "$answer" =~ ^[Yy]$ ]]; then
    read -r -s -p "Enter ${name}: " value
    echo ""
    if [ -n "$value" ]; then
      export "${name}=${value}"
      SET_VARS["$name"]="$value"
    fi
  fi
done

read -r -p "Persist these variables in your shell profile? (y/N) " persist
if [[ "$persist" =~ ^[Yy]$ ]]; then
  PROFILE_FILE="${HOME}/.bashrc"
  if [ -n "${ZSH_VERSION:-}" ]; then
    PROFILE_FILE="${HOME}/.zshrc"
  fi
  for key in "${!SET_VARS[@]}"; do
    echo "export ${key}=\"${SET_VARS[$key]}\"" >> "$PROFILE_FILE"
  done
  echo "Saved to $PROFILE_FILE. Restart your shell to pick up persisted variables."
fi

section "Done"
echo "To run:"
echo "  source .venv/bin/activate"
echo "  python -m app --self"
