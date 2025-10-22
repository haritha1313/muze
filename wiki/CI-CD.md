# CI/CD Pipeline

## Overview

Muze includes a GitHub Actions workflow for automated documentation analysis on pull requests. This document explains the CI/CD setup and how to extend it.

---

## Current Pipeline

### GitHub Actions Workflow

**File**: `.github/workflows/doc-analysis.yml`

**Trigger**: Pull requests (opened, synchronized, reopened)

**Purpose**: Analyze code changes and check for undocumented functions

---

## Workflow Configuration

### doc-analysis.yml

```yaml
name: Doc Analysis

on:
  pull_request:
    types: [opened, synchronize, reopened]

permissions:
  contents: read
  pull-requests: write

jobs:
  analyze:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0  # need merge base

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          python -V
          pip install -r scripts/requirements.txt || true

      - name: Run Analysis
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          PR_NUMBER: ${{ github.event.pull_request.number }}
          REPO: ${{ github.repository }}
          BASE_SHA: ${{ github.event.pull_request.base.sha }}
          HEAD_SHA: ${{ github.event.pull_request.head.sha }}
        run: python scripts/analyze_pr.py
```

---

## Workflow Steps

### 1. Checkout Code

```yaml
- uses: actions/checkout@v4
  with:
    fetch-depth: 0
```

**Purpose**: Clone repository with full history

**Why `fetch-depth: 0`**: Needed to compare base and head commits

---

### 2. Setup Python

```yaml
- name: Setup Python
  uses: actions/setup-python@v5
  with:
    python-version: '3.11'
```

**Purpose**: Install Python 3.11 for analysis script

**Version**: 3.11 (latest stable)

---

### 3. Install Dependencies

```yaml
- name: Install dependencies
  run: |
    python -V
    pip install -r scripts/requirements.txt || true
```

**Purpose**: Install required Python packages

**Note**: `|| true` prevents failure if requirements.txt missing

---

### 4. Run Analysis

```yaml
- name: Run Analysis
  env:
    GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
    PR_NUMBER: ${{ github.event.pull_request.number }}
    REPO: ${{ github.repository }}
    BASE_SHA: ${{ github.event.pull_request.base.sha }}
    HEAD_SHA: ${{ github.event.pull_request.head.sha }}
  run: python scripts/analyze_pr.py
```

**Purpose**: Execute documentation analysis script

**Environment Variables**:
- `GITHUB_TOKEN`: Authenticate with GitHub API
- `PR_NUMBER`: Pull request number
- `REPO`: Repository name (owner/repo)
- `BASE_SHA`: Base commit SHA
- `HEAD_SHA`: Head commit SHA

---

## Analysis Script

### scripts/update_docs.py

**Purpose**: Generate documentation for undocumented functions

**Key Functions**:

#### `generate_doc_for_function()`
```python
def generate_doc_for_function(file_path: str, function_name: str) -> str:
    mod = Path(file_path).stem
    return f"""## {function_name}

Brief description.

**Parameters:**
- ...

**Returns:**
- ...

**Example:**
```python
from {mod} import {function_name}
# {function_name}(...)
```"""
```

**Purpose**: Generate template documentation for a function

---

#### `analyze_undocumented()`
```python
def analyze_undocumented():
    import analyze_pr as analyzer
    base_sha = os.getenv('BASE_SHA')
    head_sha = os.getenv('HEAD_SHA')
    changed = analyzer.get_changed_files(base_sha, head_sha)
    results = []
    py_files = [p for p in changed if p.endswith('.py')]
    for fpath in py_files:
        if not Path(fpath).exists():
            continue
        for fn in analyzer.extract_functions_py(fpath):
            if not analyzer.is_mentioned(fn):
                results.append({'file': fpath, 'function': fn})
    return results
```

**Purpose**: Find functions added in PR that lack documentation

**Note**: Requires `analyze_pr.py` module (not currently present)

---

#### `append_docs()`
```python
def append_docs(doc_file: str, content: str):
    Path(doc_file).parent.mkdir(parents=True, exist_ok=True)
    with open(doc_file, 'a', encoding='utf-8') as f:
        f.write("\n\n## API Reference\n\n")
        f.write(content.strip())
        f.write("\n")
```

**Purpose**: Append generated docs to README

---

#### `main()`
```python
def main():
    undocumented = analyze_undocumented()
    if not undocumented:
        print("No undocumented functions.")
        return

    target = 'README.md'
    blocks = [generate_doc_for_function(it['file'], it['function']) for it in undocumented]
    append_docs(target, "\n\n".join(blocks))

    git(['git', 'config', 'user.name', 'doc-bot'])
    git(['git', 'config', 'user.email', 'bot@example.com'])
    git(['git', 'add', target])
    git(['git', 'commit', '-m', 'docs: auto-generate documentation'])
    git(['git', 'push'])
    print(f"Updated {target}")
```

**Purpose**: Main workflow - analyze, generate, commit, push

---

## Missing Components

### analyze_pr.py

**Status**: Referenced but not present in repository

**Required Functions**:
- `get_changed_files(base_sha, head_sha)` - Get files changed in PR
- `extract_functions_py(file_path)` - Parse Python file for functions
- `is_mentioned(function_name)` - Check if function is documented

**Implementation Needed**: Create this module for full functionality

---

## Extending the Pipeline

### Add Testing Workflow

**Create**: `.github/workflows/tests.yml`

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov
      
      - name: Run tests
        run: pytest tests/ --cov=. --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
```

---

### Add Linting Workflow

**Create**: `.github/workflows/lint.yml`

```yaml
name: Lint

on: [push, pull_request]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install linters
        run: |
          pip install flake8 black isort
      
      - name: Run flake8
        run: flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
      
      - name: Check black formatting
        run: black --check .
      
      - name: Check import sorting
        run: isort --check-only .
```

---

### Add Deployment Workflow

**Create**: `.github/workflows/deploy.yml`

```yaml
name: Deploy

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Deploy to production
        env:
          DEPLOY_KEY: ${{ secrets.DEPLOY_KEY }}
          SERVER_HOST: ${{ secrets.SERVER_HOST }}
        run: |
          echo "$DEPLOY_KEY" > deploy_key
          chmod 600 deploy_key
          rsync -avz -e "ssh -i deploy_key" \
            --exclude '.git' \
            --exclude '__pycache__' \
            --exclude 'snapshots' \
            . user@$SERVER_HOST:/var/www/muze/
```

---

## Secrets Management

### Required Secrets

**Location**: GitHub Repository → Settings → Secrets and variables → Actions

| Secret Name | Purpose | Example |
|-------------|---------|---------|
| `GITHUB_TOKEN` | Automatically provided | N/A |
| `ALGORITHMIA_API_KEY` | API authentication | `simABC123...` |
| `DEPLOY_KEY` | SSH key for deployment | `-----BEGIN RSA...` |
| `SERVER_HOST` | Production server address | `example.com` |

### Adding Secrets

1. Go to repository settings
2. Click "Secrets and variables" → "Actions"
3. Click "New repository secret"
4. Enter name and value
5. Click "Add secret"

---

## Environment Configuration

### Development Environment

```yaml
environment:
  name: development
  url: http://dev.muze.example.com
```

### Staging Environment

```yaml
environment:
  name: staging
  url: http://staging.muze.example.com
```

### Production Environment

```yaml
environment:
  name: production
  url: https://muze.example.com
```

---

## Workflow Triggers

### On Push

```yaml
on:
  push:
    branches:
      - main
      - develop
```

### On Pull Request

```yaml
on:
  pull_request:
    types: [opened, synchronize, reopened]
    branches:
      - main
```

### On Schedule

```yaml
on:
  schedule:
    - cron: '0 0 * * 0'  # Weekly on Sunday
```

### Manual Trigger

```yaml
on:
  workflow_dispatch:
    inputs:
      environment:
        description: 'Environment to deploy to'
        required: true
        default: 'staging'
```

---

## Status Badges

### Add to README.md

```markdown
![Tests](https://github.com/username/muze/workflows/Tests/badge.svg)
![Lint](https://github.com/username/muze/workflows/Lint/badge.svg)
![Doc Analysis](https://github.com/username/muze/workflows/Doc%20Analysis/badge.svg)
```

---

## Local Testing

### Test Workflow Locally

**Install act**:
```bash
# macOS
brew install act

# Linux
curl https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash
```

**Run workflow**:
```bash
act pull_request
```

---

## Monitoring & Notifications

### Slack Notifications

**Add to workflow**:
```yaml
- name: Notify Slack
  if: failure()
  uses: 8398a7/action-slack@v3
  with:
    status: ${{ job.status }}
    text: 'Workflow failed!'
    webhook_url: ${{ secrets.SLACK_WEBHOOK }}
```

### Email Notifications

**Add to workflow**:
```yaml
- name: Send email
  if: failure()
  uses: dawidd6/action-send-mail@v3
  with:
    server_address: smtp.gmail.com
    server_port: 465
    username: ${{ secrets.EMAIL_USERNAME }}
    password: ${{ secrets.EMAIL_PASSWORD }}
    subject: Build failed
    to: admin@example.com
    from: GitHub Actions
    body: Workflow ${{ github.workflow }} failed
```

---

## Best Practices

### 1. Cache Dependencies

```yaml
- name: Cache pip packages
  uses: actions/cache@v3
  with:
    path: ~/.cache/pip
    key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements.txt') }}
    restore-keys: |
      ${{ runner.os }}-pip-
```

### 2. Matrix Testing

```yaml
strategy:
  matrix:
    python-version: ['3.8', '3.9', '3.10', '3.11']
    os: [ubuntu-latest, windows-latest, macos-latest]
```

### 3. Conditional Steps

```yaml
- name: Deploy
  if: github.ref == 'refs/heads/main' && github.event_name == 'push'
  run: ./deploy.sh
```

### 4. Artifact Upload

```yaml
- name: Upload logs
  if: always()
  uses: actions/upload-artifact@v3
  with:
    name: logs
    path: logs/
```

### 5. Timeout Protection

```yaml
jobs:
  test:
    timeout-minutes: 10
```

---

## Troubleshooting CI/CD

### Workflow Not Triggering

**Check**:
- Workflow file syntax (use YAML validator)
- Trigger conditions match event
- Workflow file in `.github/workflows/`
- Branch protection rules

### Permission Denied

**Solution**:
```yaml
permissions:
  contents: write
  pull-requests: write
```

### Secrets Not Available

**Check**:
- Secret name matches exactly (case-sensitive)
- Secret is set at correct level (repo/org/environment)
- Workflow has access to environment

### Timeout Issues

**Solution**:
```yaml
jobs:
  test:
    timeout-minutes: 30  # Increase timeout
```

---

## Future Enhancements

### Planned Features

- [ ] Automated testing on PR
- [ ] Code coverage reporting
- [ ] Security scanning
- [ ] Dependency updates (Dependabot)
- [ ] Automated releases
- [ ] Performance benchmarking
- [ ] Docker image building
- [ ] Multi-environment deployments

### Integration Ideas

- **Codecov**: Code coverage tracking
- **SonarCloud**: Code quality analysis
- **Snyk**: Security vulnerability scanning
- **Dependabot**: Dependency updates
- **Lighthouse CI**: Performance testing
