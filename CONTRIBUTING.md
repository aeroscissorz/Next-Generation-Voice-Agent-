# Contributing Guidelines

This repository follows a strict branch-based workflow. Direct commits to the main branch are not allowed.

## Branch Policy

The main branch is reserved for stable, reviewed code only.

All development must be done on separate branches and merged through pull requests.

## Branch Naming Convention

Use one of the following formats when creating a branch:

feature/<short-description>
fix/<short-description>
experiment/<short-description>
chore/<short-description>

Examples:
feature/streaming-stt
fix/session-memory
experiment/realtime-routing
chore/update-dependencies

## Development Workflow

Clone the repository:

git clone https://github.com/aeroscissorz/Next-Generation-Voice-Agent-.git
cd Next-Generation-Voice-Agent-

Create a new branch from main:

git checkout main
git pull origin main
git checkout -b feature/your-feature-name

Make changes and commit:

git add .
git commit -m "feat: short clear description"

Push your branch:

git push -u origin feature/your-feature-name

Open a Pull Request on GitHub:

Base branch: main
Compare branch: your feature branch

## Pull Request Rules

Each pull request should focus on a single feature or fix.
Ensure the code runs and does not include local or runtime files.
Describe clearly what the change does and why it is needed.

## Prohibited Actions

Do not commit directly to the main branch.
Do not commit virtual environments, runtime artifacts, or local configuration files.
Do not force push to main.

## Code Quality

Write clear, readable code.
Keep changes minimal and scoped.
Follow existing project structure and patterns.

By contributing to this repository, you agree to follow these guidelines.
