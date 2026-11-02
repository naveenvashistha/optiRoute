# Deployment VM access

This is the one-time access setup for GitHub Actions. It does not deploy images.
Run the commands in **GCP Cloud Shell**, signed in as your personal project owner.
Keep your existing VM SSH session open until the new connection succeeds.
See [cloud setup](../docs/cloud-setup.md) for the preceding registry/VM steps and
[the pipeline walkthrough](../docs/pipeline.md) for how the workflow uses this
access after setup.

## 1. Prepare permissions and the IAP firewall rule

Upload `setup-vm-access.sh` to Cloud Shell, then run it from its upload directory:

```bash
bash setup-vm-access.sh
```

The script enables IAP and OS Login APIs, verifies the VM, and grants access to
`github-deployer` and your currently signed-in personal account:

| Grant | Scope | Purpose |
| --- | --- | --- |
| Custom `optirouteSshDiscovery` role | Project | Only `compute.instances.get`, `compute.instances.list`, and `compute.projects.get`, for gcloud SSH/SCP discovery. These can read VM/project metadata across the project. |
| `roles/compute.osAdminLogin` | `optiroute-vm` | Linux login with sudo, needed to manage Docker. This is administrator access inside this VM. |
| `roles/iap.tunnelResourceAccessor` | Project, conditioned on the VM's internal IP and port 22 | Open an authenticated SSH tunnel to that destination. Re-run setup if the VM's internal IP changes. |
| `roles/iam.serviceAccountUser` | `optiroute-runtime` service account | Required to log into a VM with this service account attached. This is actAs, not Token Creator. |

The firewall rule allows TCP 22 from Google's IAP range `35.235.240.0/20`
to VMs using `optiroute-runtime` on the default network. Existing firewall rules
remain in effect; this does not remove any broader SSH rule already present.

Docker administrator access also allows reading the VM's files and using its
runtime service account. Treat the permitted GitHub deployment workflow as
trusted administrator code. The existing OIDC restriction to this repository's
`main` branch still applies.

The script adds IAM bindings without replacing existing policies. It can be
re-run; if the named firewall rule exists with different settings, it stops.
If any command fails, stop and resolve the error before enabling OS Login.

## 2. Enable OS Login on this VM

After the setup script succeeds, run in Cloud Shell:

```bash
gcloud compute instances add-metadata optiroute-vm \
  --project=optiroute-512819 \
  --zone=asia-south1-a \
  --metadata=enable-oslogin=TRUE
```

OS Login replaces metadata-based SSH key authentication with IAM-controlled
login. It can assign a different Linux username and home directory. The existing
application directory and containers are not moved. The shared /opt deployment
directory is prepared separately in the [deployment guide](deployment.md).

## 3. Verify your own access before testing automation

From Cloud Shell, open a new connection through IAP:

```bash
gcloud compute ssh optiroute-vm \
  --project=optiroute-512819 \
  --zone=asia-south1-a \
  --tunnel-through-iap \
  --command='whoami; sudo -n whoami'
```

Expect your OS Login username followed by `root`. If permissions were just
granted, allow time for IAM propagation and retry the connection. If you cannot
log in, use Cloud Shell to temporarily disable OS Login while diagnosing it:

```bash
gcloud compute instances add-metadata optiroute-vm \
  --project=optiroute-512819 \
  --zone=asia-south1-a \
  --metadata=enable-oslogin=FALSE
```

## 4. Verify GitHub's access

Merge the updated **Check GCP authentication** workflow into `main`, then run it
manually from GitHub Actions. It authenticates as `github-deployer` through the
existing OIDC setup and checks SSH and passwordless sudo over IAP. It does not
update containers or access application secrets.

References: [OS Login setup](https://docs.cloud.google.com/compute/docs/oslogin/set-up-oslogin),
[IAP TCP forwarding](https://docs.cloud.google.com/iap/docs/using-tcp-forwarding).
