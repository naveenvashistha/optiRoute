#!/usr/bin/env bash
# Run once in Cloud Shell as the project owner, not inside the VM or CI.
set -euo pipefail

PROJECT_ID=optiroute-512819
ZONE=asia-south1-a
VM=optiroute-vm
NETWORK=default
DEPLOYER="github-deployer@${PROJECT_ID}.iam.gserviceaccount.com"
RUNTIME="optiroute-runtime@${PROJECT_ID}.iam.gserviceaccount.com"
DISCOVERY_ROLE=optirouteSshDiscovery
FIREWALL=optiroute-allow-iap-ssh

operator=$(gcloud auth list --filter=status:ACTIVE --format='value(account)')
impersonation=$(gcloud config get-value auth/impersonate_service_account 2>/dev/null)
if [[ -z "$operator" || "$operator" == *gserviceaccount.com || "$operator" == *$'\n'* ]]; then
  echo 'Run this in Cloud Shell with your personal project-owner account.' >&2
  exit 1
fi
if [[ -n "$impersonation" && "$impersonation" != '(unset)' ]]; then
  echo 'Use a Cloud Shell configuration without service-account impersonation.' >&2
  exit 1
fi

gcloud services enable iap.googleapis.com oslogin.googleapis.com \
  --project="$PROJECT_ID"

# Check the actual VM before granting access or changing its login settings.
instance=$(gcloud compute instances describe "$VM" --zone="$ZONE" \
  --project="$PROJECT_ID" --format=json)
jq -e --arg runtime "$RUNTIME" --arg network "$NETWORK" '
  .status == "RUNNING" and
  .serviceAccounts[0].email == $runtime and
  (.networkInterfaces[0].network | endswith("/networks/" + $network))
' <<< "$instance" >/dev/null
internal_ip=$(jq -er '.networkInterfaces[0].networkIP' <<< "$instance")

# gcloud needs these read-only discovery permissions even with VM-scoped login.
roles=$(gcloud iam roles list --project="$PROJECT_ID" --format='value(name)')
role_action=create
if [[ "$roles" == *"projects/${PROJECT_ID}/roles/${DISCOVERY_ROLE}"* ]]; then
  role_action=update
fi
gcloud iam roles "$role_action" "$DISCOVERY_ROLE" --project="$PROJECT_ID" \
  --title='OptiRoute SSH discovery' --stage=GA \
  --description='Read VM and project details required by gcloud SSH and SCP.' \
  --permissions=compute.instances.get,compute.instances.list,compute.projects.get

# Add bindings rather than replacing existing IAM policies. Preserve human
# access before OS Login stops accepting metadata-based SSH keys.
for member in "serviceAccount:$DEPLOYER" "user:$operator"; do
  gcloud projects add-iam-policy-binding "$PROJECT_ID" --member="$member" \
    --role="projects/${PROJECT_ID}/roles/${DISCOVERY_ROLE}" --condition=None

  gcloud compute instances add-iam-policy-binding "$VM" --zone="$ZONE" \
    --project="$PROJECT_ID" --member="$member" \
    --role=roles/compute.osAdminLogin --condition=None

  # The tunnel is limited to SSH on this VM's current internal IPv4 address.
  gcloud projects add-iam-policy-binding "$PROJECT_ID" --member="$member" \
    --role=roles/iap.tunnelResourceAccessor \
    --condition="title=optiroute-vm-ssh,expression=destination.ip == '${internal_ip}' && destination.port == 22"

  # OS Login requires actAs on the service account attached to the VM.
  gcloud iam service-accounts add-iam-policy-binding "$RUNTIME" \
    --project="$PROJECT_ID" --member="$member" \
    --role=roles/iam.serviceAccountUser --condition=None
done

existing_firewall=$(gcloud compute firewall-rules list --project="$PROJECT_ID" \
  --filter="name=$FIREWALL" --format=json)
if [[ "$(jq 'length' <<< "$existing_firewall")" == 0 ]]; then
  gcloud compute firewall-rules create "$FIREWALL" --project="$PROJECT_ID" \
    --network="$NETWORK" --direction=INGRESS --allow=tcp:22 \
    --source-ranges=35.235.240.0/20 --target-service-accounts="$RUNTIME"
else
  # Do not silently overwrite a rule that differs from the expected setup.
  jq -e --arg runtime "$RUNTIME" --arg network "$NETWORK" '
    length == 1 and (.[0] |
      .direction == "INGRESS" and (.disabled != true) and
      (.network | endswith("/networks/" + $network)) and
      .sourceRanges == ["35.235.240.0/20"] and
      .targetServiceAccounts == [$runtime] and
      .allowed == [{"IPProtocol":"tcp","ports":["22"]}])
  ' <<< "$existing_firewall" >/dev/null || {
    echo "Existing firewall rule $FIREWALL differs; inspect it before continuing." >&2
    exit 1
  }
fi

# Deliberately separate this from enabling OS Login, so the grants can be reviewed.
printf '\nAccess permissions prepared for %s and %s.\n' "$DEPLOYER" "$operator"
printf 'Next: follow deploy/vm-access.md to enable OS Login and test a new connection.\n'
