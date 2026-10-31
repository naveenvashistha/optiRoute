# Deploying a release on the VM

`deploy.sh` runs on the VM as root. It accepts the full 40-character commit SHA
whose frontend and backend images have both been successfully published.
It does not build images or pick the newest release automatically.

For the complete setup and rationale, read [cloud setup](../docs/cloud-setup.md),
[the pipeline walkthrough](../docs/pipeline.md), and
[operations/troubleshooting](../docs/operations.md). This page focuses on the
one-time application-directory preparation and the release invocation.

## One-time preparation of /opt/optiroute

Run these commands in the **VM SSH terminal**, after OS Login access is working.
The source is the original application's location, not your new OS Login home.
Do this copy once; on later releases keep the environment files already in /opt.

```bash
sudo install -d -o root -g root -m 700 \
  /opt/optiroute /opt/optiroute/backend /opt/optiroute/deploy

sudo install -o root -g root -m 600 \
  /home/naveenvashistha2000/optiroute/.env /opt/optiroute/.env
sudo install -o root -g root -m 600 \
  /home/naveenvashistha2000/optiroute/backend/.env /opt/optiroute/backend/.env

sudo install -o root -g root -m 644 \
  /home/naveenvashistha2000/optiroute/compose.yaml \
  /home/naveenvashistha2000/optiroute/compose.production.yaml \
  /opt/optiroute/
sudo install -o root -g root -m 644 \
  /home/naveenvashistha2000/optiroute/deploy/nginx-trusted-proxy.conf \
  /home/naveenvashistha2000/optiroute/deploy/nginx-forwarded-scheme.map \
  /opt/optiroute/deploy/
```

For an optional manual test, upload the new local `deploy/deploy.sh` file using
the VM browser SSH upload button. From the home directory where it was uploaded,
install it as shown below. Automatic deployments upload this script themselves,
so you can skip this manual script installation when using GitHub Actions.

```bash
sudo install -o root -g root -m 700 deploy.sh /opt/optiroute/deploy/deploy.sh
```

This preparation copies files without stopping containers. Keep the original
directory until the first deployment from /opt succeeds. The script explicitly
uses Compose project name `optiroute`, so it updates the existing application.
The first run also switches the frontend bind mounts to their /opt paths.
Caddy remains managed by systemd and needs no change for this directory copy.

The VM needs Docker with the Compose plugin, curl, jq, and flock (util-linux).
Docker, curl, and jq were used during the earlier setup. If flock is missing:

```bash
sudo apt-get update
sudo apt-get install -y util-linux
```

## Deploy an already-published release

Set the exact commit SHA displayed by the successful image-publishing workflow.
Use only the SHA, without an image name or `@sha256:` digest:

```bash
IMAGE_TAG='REPLACE_WITH_THE_PUBLISHED_40_CHARACTER_COMMIT_SHA'
sudo bash /opt/optiroute/deploy/deploy.sh "$IMAGE_TAG"
```

The script:

1. Validates its input, required files, tools, and Compose configuration without
   printing the resolved configuration (which includes backend secrets).
2. Locks the deployment directory so only one deployment script runs at a time.
3. Verifies the attached runtime account, obtains its access token from the GCP
   metadata service, and logs Docker into Artifact Registry. A temporary Docker
   configuration is deleted on exit; existing Docker login settings are untouched.
4. Pulls both selected application images, and Redis only if missing, before
   changing containers or the root .env. A download failure leaves the running
   containers and release selection unchanged.
5. Saves the previous root .env as `.env.previous`, then replaces only IMAGE_TAG
   in .env. Backend API credentials in `backend/.env` remain on the VM.
6. Runs Compose with `--no-build --pull never --wait --wait-timeout 300` and
   checks `/api/ready` through frontend Nginx. Failures return a nonzero exit code.

After success, check the public entry point and try one chat in your browser:

```bash
curl -fsS --connect-timeout 5 --max-time 15 https://optiroutee.tech/api/ready
```

This single-VM update can briefly interrupt requests while containers restart.
It does not run `compose down`, prune images, or automatically roll back. After
a startup/readiness failure, .env records the attempted release, and containers
may be partially updated. `.env.previous` preserves the previous environment
selection from the most recent attempt; it is not a full configuration backup.
Release history and rollback automation are intentionally out of scope.

## Automatic deployment from GitHub

After the one-time /opt preparation above, push or merge these files into main,
including `deploy.sh`. The **Build and deploy OptiRoute** workflow automatically:

1. Builds and publishes frontend and backend images tagged with that commit SHA.
2. Starts its deployment job only if both publish jobs succeed.
3. Authenticates as github-deployer through OIDC, then connects using IAP/OS Login.
4. Uploads an archive containing only the two Compose files, deployment script,
   and two Nginx proxy files into the deployment account's home directory.
5. Runs the uploaded script with the SHA and the absolute staging directory.
   Under the deployment lock, the script validates the staged configuration,
   downloads the images, installs the versioned files into /opt/optiroute, and
   updates containers. Environment files are read from /opt and never uploaded.
6. Checks readiness from the GitHub runner through the public HTTPS address.

The temporary upload directory is removed after the remote deployment command
finishes, including failures. If the connection fails before that command starts,
a staging directory can remain in the deployment account's home for later cleanup.
The entire workflow uses a production concurrency group with cancellation off,
so new runs do not interrupt an active deployment. By default GitHub keeps only
one pending run, replacing it when another arrives. A commit that is no longer
the main branch head at the pre-deployment check is skipped to avoid deploying an
old rerun. A new push after that check waits for the current workflow to finish.

You can also use **Run workflow** on main to build and deploy its current commit.
Manual image publishing through this workflow now includes deployment. Once the
workflow is merged, file uploads and script invocation are automatic for releases.
The server's /opt directory and both environment files must already exist before
the first run. The script itself no longer needs to be uploaded manually for CI.
