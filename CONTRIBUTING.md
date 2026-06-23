Contributing
============

Thank you for considering contributing! This project is designed to be small and local-first. Contributions that improve usability, documentation, and model integration are welcome.

Getting started
---------------
1. Fork the repo and create a branch for your change.
2. Create a Python virtual environment and install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

3. Run the app locally:

```bash
.venv/bin/python app.py
```

Model guidelines
----------------
- This repository does not include large model binaries. If you add instructions or tooling for model download or packaging, document size, license, and privacy implications clearly.
- Prefer optional integrations (e.g., enable via `ALLOW_MODEL_DOWNLOAD=true`) rather than making downloads automatic.

Code style & tests
------------------
- Keep changes small and focused. Add tests for behavioral changes where relevant.
- If you add new dependencies, include rationale in your PR description.

Pull requests
-------------
- Open a PR against `main` with a clear description and testing steps.
- For large model-support changes, include documentation in `models/README.md`.
