# OptiRoute

## Runtimes and dependencies

Use Python 3.11 for the backend and Node.js 22 (at least 22.13.0) with npm 10
for the frontend. The version files select these runtime families; they do not
lock a specific patch release. The existing environment was checked with
Python 3.11.4, Node.js 22.18.0, and npm 10.9.3.

### Backend

Create and activate a Python 3.11 virtual environment before installing packages.
From `backend`, install the CPU build of PyTorch first, then the other dependencies:

```sh
python -m pip install "torch==2.13.0" --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r requirements.txt
python -m pip check
```

Keep this order in the deployment build so the general PyPI installation does not
select a CUDA build for the CPU server. The CPU wheel is available for Python 3.11
on Windows and Linux x86-64.

`requirements.txt` pins the application's direct dependencies to the existing
environment. It is not a complete lock of transitive dependencies. A clean Linux
container installation still needs verification during container setup.

The saved intent classifier contains scikit-learn 1.0.2 metadata, while the current
environment uses 1.9.0. A local load and prediction check passes, but scikit-learn
reports an incompatible-version warning. These pins preserve the current runtime;
they do not resolve the model's serialization compatibility warning.

### Frontend

From `frontend`, use the committed lockfile for fresh development and CI installs:

```sh
npm ci
npm run build
```

`npm ci` replaces `node_modules` and installs the versions recorded in
`package-lock.json`. Use `npm install` when intentionally updating dependencies,
and review and commit the resulting lockfile changes.
