# Overmind Setup (Windows + macOS/Linux)

This guide installs the backend, builds the UI, and configures API keys.

## Prerequisites

- Python 3.10+ (Windows: `py -3`, macOS/Linux: `python3`)
- Node.js 18+ and npm
- Git (optional but recommended)

## Quick Setup (recommended)

### Windows (PowerShell)

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\setup.ps1
```

### macOS/Linux (bash/zsh)

```bash
chmod +x ./setup.sh
./setup.sh
```

The scripts will:

- Create a `.venv` virtual environment
- Install Python dependencies from `requirements.txt`
- Install UI dependencies and build the UI bundle
- Prompt for provider API keys and set environment variables

## Run the App

Activate the virtual environment (if the script is not already running):

### Windows

```powershell
.\.venv\Scripts\Activate.ps1
```

### macOS/Linux

```bash
source .venv/bin/activate
```

Start the server:

```bash
python -m app --self
```

Open:

```
http://127.0.0.1:8000
```

## Team Commands

- `@break`: pause all agent work for the active run.
- `@attention`: pause work and call a team meeting (await instructions).
- `@resume`: resume work (any stakeholder message also resumes).

## Manual Setup (no scripts)

### 1) Create and activate a venv

```bash
python -m venv .venv
```

Activate:

- Windows: `.\.venv\Scripts\Activate.ps1`
- macOS/Linux: `source .venv/bin/activate`

### 2) Install backend deps

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 3) Build the UI

```bash
cd ui
npm install
npm run build
cd ..
```

### 4) Configure environment variables

These are used by the provider integrations. You can set only the ones you need.

- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`
- `GROQ_API_KEY`
- `GEMINI_API_KEY`

Optional:

- `AI_DEVTEAM_ENV` (default: `dev`)
- `AI_DEVTEAM_ALLOW_SELF_EDIT` (default: `true`)
- `AI_DEVTEAM_ALLOW_SELF_PROJECT` (default: `false`)
- `AI_DEVTEAM_GENERATE_PROFILES` (default: `true`)
- `AI_DEVTEAM_REPO_ROOT` (defaults to current directory)

### Windows example (PowerShell)

```powershell
$env:OPENAI_API_KEY = "sk-..."
```

### macOS/Linux example

```bash
export OPENAI_API_KEY="sk-..."
```

## Troubleshooting

- If the UI still shows old assets, hard refresh the browser.
- If PowerShell blocks script execution, use:
  `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`
