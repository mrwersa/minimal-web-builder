# Contributing

Thanks for contributing to Minimal Web Builder.

## Workflow

1. Create a branch from main.
2. Open a pull request.
3. Get at least one approval.
4. Ensure all required checks pass.
5. Resolve all review conversations.
6. Merge using squash or rebase (linear history is required).

Direct pushes to main are blocked by branch protection.

## Local Development

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Pull Request Quality Bar

- Keep the product minimal and focused.
- Prefer simple, explicit code over clever abstractions.
- Preserve self-contained HTML/CSS/JS output.
- Add or update tests for behavior changes.
- Update README or docs when user-facing behavior changes.

## Suggested PR Sizes

- Small (recommended): one focused improvement.
- Medium: one feature plus tests/docs.
- Large: only when coordinated with maintainers.
