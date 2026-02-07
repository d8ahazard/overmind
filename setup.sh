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

# Find suitable Python version (3.11-3.13, avoid 3.14)
find_python() {
  for py in python3.13 python3.12 python3.11 python3.10 python3.9 python3 python; do
    if command -v "$py" >/dev/null 2>&1; then
      version=$("$py" --version 2>&1 | awk "{print \$2}" | cut -d. -f1,2)
      major=$(echo "$version" | cut -d. -f1)
      minor=$(echo "$version" | cut -d. -f2)
      
      # Check if version is 3.11-3.13
      if [ "$major" = "3" ] && [ "$minor" -ge 11 ] && [ "$minor" -le 13 ]; then
        echo "$py"
        return 0
      fi
    fi
  done
  return 1
}

PYTHON_BIN=$(find_python)

if [ -z "$PYTHON_BIN" ]; then
  echo "❌ No compatible Python found. Overmind requires Python 3.11-3.13"
  echo ""
  echo "You may have Python 3.14 which is not yet supported by dependencies."
  echo ""
  echo "To install Python 3.13:"
  echo "  Mac:     brew install python@3.13"
  echo "  Linux:   sudo apt install python3.13  or  pyenv install 3.13.2"
  echo "  Windows: https://www.python.org/downloads/release/python-3132/"
  echo ""
  echo "Or set PYTHON_BIN manually:"
  echo "  PYTHON_BIN=/path/to/python3.13 ./setup.sh"
  exit 1
fi

echo "✅ Using Python: $PYTHON_BIN"
"$PYTHON_BIN" --version

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
