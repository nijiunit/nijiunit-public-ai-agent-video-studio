# Security policy

## Secrets

- Put API keys only in an untracked `.env` or environment variable.
- Never place keys in prompts, storyboards, workbooks, logs, screenshots, or
  character metadata.
- Treat generated provider metadata as potentially sensitive before publishing.
- Rotate a key immediately if it appears in Git history.

The repository ignores `.env`, `input`, `output`, temporary data, and logs by
default. `.env.example` contains names only and must never contain a real value.

## Reporting

Please report a suspected vulnerability privately to the repository owner using
GitHub's private vulnerability reporting feature. Do not open a public issue
that contains credentials or personal data.

