# GCP setup, first deployment, DNS, and HTTPS

This records the cloud setup built during the project. Creation commands are
for a new setup, not a script to rerun against the working deployment. When a
resource already exists, inspect/reuse it rather than trying to create it again.
Commands in this guide use Bash unless a block is explicitly PowerShell.

## Where commands run

| Environment | Purpose |
| --- | --- |
| Laptop/repository | Edit code, commit/merge, build local images, and inspect GitHub Actions. |
| GCP Cloud Shell | Configure project APIs, service accounts, IAM, workload identity, VM, IP, and cloud firewall. It uses your signed-in Google identity. |
| VM SSH terminal | Install Docker/Caddy, manage host files, run Compose, and inspect application containers. Its attached service account is the restricted runtime identity. |
| GitHub-hosted runner | Build/publish images and deploy automatically through OIDC and IAP. |

VM administrator access does not automatically give the VM's runtime service
account permission to administer GCP IAM. Run cloud-management commands from
Cloud Shell, not from a metadata-authenticated VM shell.

## Resource inventory

| Setting | Value used |
| --- | --- |
| GCP project ID | `optiroute-512819` |
| Region / zone | `asia-south1` / `asia-south1-a` |
| VM / VPC | `optiroute-vm` / existing `default` network and regional default subnet |
| Registry repository | `asia-south1-docker.pkg.dev/optiroute-512819/optiroute` |
| GitHub repository / deployment branch | `naveenvashistha/optiRoute` / `main` |
| Repository ID / owner ID | `1333473371` / `65558609` |
| Workload identity pool / provider | `github-actions` / `github` in `global` |
| Deployer account | `github-deployer@optiroute-512819.iam.gserviceaccount.com` |
| Runtime account | `optiroute-runtime@optiroute-512819.iam.gserviceaccount.com` |
| Domain / reserved external IPv4 | `optiroutee.tech` / `34.100.181.134` |
| Final deployment directory | `/opt/optiroute` |

The numeric GCP project number is different from the project ID; discover it
with the command below. The exact final VM machine type/OS image was not captured
in the chat. Inspect the running instance rather than inferring it from an
earlier console screenshot.

## 1. Create the account/project and enable APIs

The project needs billing enabled to use the VM and registry. Check the account's
current trial/credit conditions in the billing console; this guide does not
promise that the deployment remains free or quote historical prices.

In **Cloud Shell**:

```bash
PROJECT_ID=optiroute-512819
gcloud config set project "$PROJECT_ID"
PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')

gcloud services enable \
  iam.googleapis.com \
  cloudresourcemanager.googleapis.com \
  iamcredentials.googleapis.com \
  sts.googleapis.com \
  artifactregistry.googleapis.com \
  compute.googleapis.com \
  iap.googleapis.com \
  oslogin.googleapis.com \
  --project="$PROJECT_ID"
```

IAM manages permissions and identities, STS exchanges external credentials,
IAM Credentials issues short-lived service-account credentials, Artifact
Registry stores images, Compute Engine hosts the VM, and IAP/OS Login enable
the authenticated administrative connection used by deployment.

## 2. Create the GitHub deployment identity

Still in **Cloud Shell**, with PROJECT_ID/PROJECT_NUMBER set as above:

```bash
gcloud iam service-accounts create github-deployer \
  --project="$PROJECT_ID" --display-name='GitHub deployment account'

gcloud iam workload-identity-pools create github-actions \
  --project="$PROJECT_ID" --location=global --display-name='GitHub Actions'

gcloud iam workload-identity-pools providers create-oidc github \
  --project="$PROJECT_ID" --location=global \
  --workload-identity-pool=github-actions \
  --issuer-uri=https://token.actions.githubusercontent.com \
  --attribute-mapping='google.subject=assertion.sub,attribute.repository_id=assertion.repository_id,attribute.repository_owner_id=assertion.repository_owner_id,attribute.ref=assertion.ref' \
  --attribute-condition="assertion.repository_owner_id == '65558609' && assertion.repository_id == '1333473371' && assertion.ref == 'refs/heads/main'"

gcloud iam service-accounts add-iam-policy-binding \
  "github-deployer@${PROJECT_ID}.iam.gserviceaccount.com" \
  --project="$PROJECT_ID" --role=roles/iam.workloadIdentityUser \
  --member="principalSet://iam.googleapis.com/projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/github-actions/attribute.repository_id/1333473371"
```

For another repository, look up and substitute its numeric repository and owner
IDs in both the provider condition and the service-account binding. The branch
condition must also match the workflow's deployment branch. If the repository
is public, its IDs can be checked without supplying GitHub credentials:

```bash
curl -fsS https://api.github.com/repos/naveenvashistha/optiRoute \
  | jq '{full_name, repository_id: .id, owner_id: .owner.id, default_branch}'
```

For a private repository, use GitHub CLI in a shell where you are authenticated
and have repository access:

```bash
gh api repos/naveenvashistha/optiRoute \
  --jq '{full_name, repository_id: .id, owner_id: .owner.id, default_branch}'
```

The pool is the container for external workload identities. The provider trusts
GitHub's issuer, maps token claims to Google attributes, and applies the owner,
repository, and branch checks. The IAM binding then allows that matching
repository identity to impersonate github-deployer. It does not grant permission
to publish images or administer the VM by itself; those grants come separately.

## 3. Set the GitHub repository variable

In GitHub, open **Settings → Secrets and variables → Actions → Variables** and
create the repository variable `GCP_WORKLOAD_IDENTITY_PROVIDER` with this value:

```text
projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/github-actions/providers/github
```

Replace PROJECT_NUMBER with the discovered number. You can obtain the complete
provider resource name directly in Cloud Shell:

```bash
gcloud iam workload-identity-pools providers describe github \
  --project=optiroute-512819 --location=global \
  --workload-identity-pool=github-actions --format='value(name)'
```

This is a resource identifier, not a secret. Do not create/download a service
account JSON key for the workflow. Each job has `id-token: write` to obtain a
GitHub identity token and `contents: read` to check out the repository.

## 4. Create the private container registry

In **Cloud Shell**:

```bash
gcloud artifacts repositories create optiroute \
  --project=optiroute-512819 --location=asia-south1 \
  --repository-format=docker --disable-vulnerability-scanning \
  --description='OptiRoute application images'

gcloud artifacts repositories add-iam-policy-binding optiroute \
  --project=optiroute-512819 --location=asia-south1 \
  --member=serviceAccount:github-deployer@optiroute-512819.iam.gserviceaccount.com \
  --role=roles/artifactregistry.writer
```

Scanning was disabled in this demo setup; no automated vulnerability-scanning
gate is claimed. Writer is scoped to this repository. Artifact Registry was
chosen to integrate registry access with the existing GCP identities and VM;
GitHub Container Registry would also be a valid registry with different access
configuration.

The application images are stored as:

```text
asia-south1-docker.pkg.dev/optiroute-512819/optiroute/frontend:<commit-sha>
asia-south1-docker.pkg.dev/optiroute-512819/optiroute/backend:<commit-sha>
```

The original workflow first verified authentication, then published images
manually. The final workflow now builds and deploys automatically on main.
The current authentication-check workflow also tests VM access, so run it only
after completing the VM-access setup below.

## 5. Create a separate VM runtime account

In **Cloud Shell**:

```bash
gcloud iam service-accounts create optiroute-runtime \
  --project=optiroute-512819 --display-name='OptiRoute VM runtime'

gcloud artifacts repositories add-iam-policy-binding optiroute \
  --project=optiroute-512819 --location=asia-south1 \
  --member=serviceAccount:optiroute-runtime@optiroute-512819.iam.gserviceaccount.com \
  --role=roles/artifactregistry.reader
```

The runtime account can pull images; it does not need the deployer's publishing
or project-administration permissions. This separates the identity used by the
running machine from the identity used by the build/deployment pipeline.

## 6. Create the VM

The VM was created in the GCP console. Use the following configuration when
reconstructing the setup:

- Name `optiroute-vm`, region Mumbai `asia-south1`, zone `asia-south1-a`.
- Linux x86-64/amd64, compatible with the published `linux/amd64` images.
- Ubuntu LTS was selected during setup; record the exact image actually used.
- A machine with room for the configured 2 GiB backend, 512 MiB Redis, 128 MiB
  frontend, and host overhead. Container limits are not the VM's total sizing.
- The boot-disk dialog shown during setup used a 30 GB balanced persistent disk;
  verify the final disk configuration instead of assuming it was unchanged.
- Network `default`, the matching regional subnet, and an external IPv4 address.
- Attached service account `optiroute-runtime`, with the `cloud-platform` API
  access scope; IAM still limits its actual permissions to registry reading.

In **Cloud Shell**, inspect the working configuration:

```bash
gcloud compute instances describe optiroute-vm \
  --project=optiroute-512819 --zone=asia-south1-a \
  --format='yaml(name,machineType,disks,networkInterfaces,serviceAccounts)'

gcloud compute disks list --project=optiroute-512819 \
  --format='table(name,zone.basename(),sizeGb,type.basename(),sourceImage)'
```

The console temporarily failed to show the existing default network during
setup. That was a loading/connectivity issue in this session, not proof that
the VPC was missing. No custom VPC is required by the current deployment.

## 7. Install Docker and supporting tools

Run in the **VM SSH terminal**, not Cloud Shell. These commands target Ubuntu
using Docker's official apt repository; inspect `/etc/os-release` first if the
actual VM uses a different distribution.

```bash
cat /etc/os-release
sudo apt-get update
sudo apt-get install -y ca-certificates curl jq util-linux
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
  -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

sudo tee /etc/apt/sources.list.d/docker.sources >/dev/null <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}")
Components: stable
Architectures: $(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/docker.asc
EOF

sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io \
  docker-buildx-plugin docker-compose-plugin
sudo systemctl enable --now docker
sudo docker run --rm hello-world
sudo docker compose version
```

If conflicting Docker packages already exist, follow Docker's installation
instructions before switching package sources. The intermittent sudo issue seen
in this session is documented in the [operations guide](operations.md).

## 8. First manual image pull and Compose deployment

This was the learning stage before CD automation. It is not required for each
release once the workflow is working. In the **VM SSH terminal**, verify the
attached identity and log Docker in with a fresh metadata access token:

```bash
curl -fsS -H 'Metadata-Flavor: Google' \
  http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/email

set -o pipefail
curl -fsS -H 'Metadata-Flavor: Google' \
  http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token \
  | jq -er '.access_token' \
  | sudo docker login --username oauth2accesstoken --password-stdin \
      asia-south1-docker.pkg.dev
```

The email must be optiroute-runtime. Never print/share the token. This manual
login writes to root's Docker configuration because Docker is run with sudo.
Access tokens expire; deployment automation instead creates and deletes a
temporary Docker configuration on every run.

Set IMAGE_TAG to the SHA of a workflow that successfully published **both**
images. The SHA is the same for both; image digests are different:

```bash
IMAGE_TAG='REPLACE_WITH_THE_PUBLISHED_40_CHARACTER_COMMIT_SHA'
sudo docker pull "asia-south1-docker.pkg.dev/optiroute-512819/optiroute/frontend:${IMAGE_TAG}"
sudo docker pull "asia-south1-docker.pkg.dev/optiroute-512819/optiroute/backend:${IMAGE_TAG}"
```

The initial working files were uploaded into `~/optiroute` in the original
human SSH account. The required layout, using the final production config, is:

```text
optiroute/
  .env                       # IMAGE_TAG only
  compose.yaml
  compose.production.yaml
  backend/.env               # Real runtime configuration, never committed
  deploy/nginx-trusted-proxy.conf
  deploy/nginx-forwarded-scheme.map
```

Create the directories, upload the versioned files, and create backend/.env
from the safe template with your working provider settings. To save in nano,
Ctrl+O opens the filename prompt, Enter confirms it, and Ctrl+X exits.
Protect environment files with `chmod 600` and their directory with `chmod 700`.
Within this initial directory, write the release selection and validate/run:

```bash
printf 'IMAGE_TAG=%s\n' "$IMAGE_TAG" > .env
chmod 600 .env backend/.env

sudo docker compose --env-file .env \
  -f compose.yaml -f compose.production.yaml config --quiet
sudo docker compose --env-file .env \
  -f compose.yaml -f compose.production.yaml \
  up -d --wait --wait-timeout 300

curl -fsS http://127.0.0.1:8080/api/ready
```

Expected readiness is `{"status":"ready"}`. Use `config --quiet`, because the
full resolved configuration contains backend environment values. Explicit
`-f` ordering selects the registry images; Compose does not discover the
production file because a local image is missing.

## 9. Reserve the external IP and set DNS

The VM initially had ephemeral address `34.100.181.134`. It was promoted to a
regional static reservation so the domain does not depend on an address that
may change after VM stop/start. Inspect existing reservations in **Cloud Shell**:

```bash
gcloud compute addresses list --project=optiroute-512819 \
  --filter='region:asia-south1' --format='table(name,address,status,users)'
```

For a still-ephemeral address on a new setup, promote the actual assigned IP:

```bash
gcloud compute addresses create optiroute-ip \
  --project=optiroute-512819 --region=asia-south1 \
  --addresses=34.100.181.134 --network-tier=PREMIUM
```

The name optiroute-ip was suggested during setup; verify the actual reservation
name in the output. Do not rerun creation if the address is already reserved.

The domain was registered through Name.com. With DNS hosted by its nameservers,
the root-domain record is:

| Type | Host/name | Answer | TTL |
| --- | --- | --- | --- |
| A | Blank (root/apex on Name.com) | `34.100.181.134` | 300 seconds |

Nameservers decide who hosts the authoritative DNS zone. The A record maps this
hostname to the server's IPv4 address. Registering a domain alone does not point
it at the VM. Resolver caching means an update may not be visible everywhere
immediately. Ensure no conflicting root A/AAAA record points at another server.
This setup configures only optiroutee.tech, not www.optiroutee.tech.

Check from **Windows PowerShell**:

```powershell
Resolve-DnsName -Name optiroutee.tech -Type A -DnsOnly
```

Or from a shell with dig:

```bash
dig +short optiroutee.tech A
```

The answer should include `34.100.181.134`.

## 10. Open public web traffic

Run in **Cloud Shell**:

```bash
gcloud compute firewall-rules create optiroute-allow-web \
  --project=optiroute-512819 --network=default --direction=INGRESS \
  --allow=tcp:80,tcp:443 --source-ranges=0.0.0.0/0 \
  --target-service-accounts=optiroute-runtime@optiroute-512819.iam.gserviceaccount.com
```

Port 80 supports HTTP redirects/certificate validation; port 443 serves HTTPS.
The target is the VM's runtime service account. No backend or Redis port is
opened. UDP 443/HTTP3 was not required/configured. Existing firewall rules still
apply, including any default broad SSH rule; adding an IAP rule alone does not
remove that other access path.

## 11. Install and configure Caddy

Install on the **VM host**, alongside Docker:

```bash
sudo apt-get install -y debian-keyring debian-archive-keyring apt-transport-https curl gnupg
curl -1sLf https://dl.cloudsmith.io/public/caddy/stable/gpg.key \
  | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt \
  | sudo tee /etc/apt/sources.list.d/caddy-stable.list >/dev/null
sudo chmod o+r /usr/share/keyrings/caddy-stable-archive-keyring.gpg
sudo chmod o+r /etc/apt/sources.list.d/caddy-stable.list
sudo apt-get update
sudo apt-get install -y caddy
```

The gnupg package supplies gpg on minimal images. The official Caddy
package installs the caddy systemd service and its persistent certificate
storage. These installation steps are one-time setup, not part of image builds.

### Configure Caddy

Edit `/etc/caddy/Caddyfile` on the VM to contain:

```caddyfile
optiroutee.tech {
    reverse_proxy 127.0.0.1:8080
}
```

Validate and reload:

```bash
sudo caddy fmt --overwrite /etc/caddy/Caddyfile
sudo caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
sudo systemctl reload caddy
sudo journalctl -u caddy -n 50 --no-pager
```

Caddy obtains and renews certificates automatically when DNS/ports allow it.
We did not buy or install a registrar SSL certificate. The browser-to-Caddy
connection is HTTPS; host loopback and internal Docker proxy connections use
HTTP. Forwarded headers preserve the visitor's original IP and scheme.

```bash
curl -I http://optiroutee.tech
curl -fsS https://optiroutee.tech/api/ready
```

Expect an HTTPS Location redirect for the first request and ready JSON for the
second. Open the HTTPS site in your laptop browser and try one streaming chat.

## 12. Enable deployment SSH access and move to /opt

Follow [VM access](../deploy/vm-access.md) to run setup-vm-access.sh in Cloud
Shell, grant permissions, enable OS Login, and test a fresh SSH connection.
Then run **Check GCP authentication** on main in GitHub Actions. The user verified
that this workflow can log in and execute passwordless sudo.

Follow the [deployment guide](../deploy/deployment.md) to copy the working files
and private environment configuration into root-owned `/opt/optiroute`. This
absolute path is the same for all Linux users; OS Login assigns the deployment
account its own username/home automatically. The original personal directory
is not the deployment account's home.

## 13. Enable the final CI/CD workflow

Commit the Dockerfiles, Compose files, proxy files, deploy.sh, and workflows.
The existing **Build and deploy OptiRoute** workflow runs on push to main and
manual dispatch. It builds both images before deploying, then checks local and
public readiness. See [Pipeline walkthrough](pipeline.md) for each job/command.
For normal releases, push/merge to main and inspect GitHub Actions; no image
upload, VM login, or manual tag editing is needed.

## Official references

- [GitHub OIDC with Google Cloud](https://docs.github.com/en/actions/how-tos/secure-your-work/security-harden-deployments/oidc-in-google-cloud-platform).
- [Google GitHub authentication action](https://github.com/google-github-actions/auth).
- [Artifact Registry Docker authentication](https://docs.cloud.google.com/artifact-registry/docs/docker/authentication).
- [Docker Engine on Ubuntu](https://docs.docker.com/engine/install/ubuntu/).
- [Caddy installation](https://caddyserver.com/docs/install) and [automatic HTTPS](https://caddyserver.com/docs/automatic-https).
- [IAP TCP forwarding](https://docs.cloud.google.com/iap/docs/using-tcp-forwarding) and [OS Login](https://docs.cloud.google.com/compute/docs/oslogin/set-up-oslogin).
