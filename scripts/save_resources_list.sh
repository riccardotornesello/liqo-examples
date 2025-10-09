#!/bin/bash

# This script saves the list of Liqo resources from both consumer and provider clusters.
# It retrieves the resources and saves the complete list of each type to a file.
# The output files are named according to the cluster and resource type (e.g., consumer_gatewayclients) and stored in the out/list directory.

set -euo pipefail

declare -A CLUSTERS
CLUSTERS["consumer"]="liqo_kubeconf_rome"
CLUSTERS["provider"]="liqo_kubeconf_milan"

RESOURCES=(
  "gatewayclients"
  "gatewayservers"
  "configurations"
  "internalnodes"
  "internalfabrics"
  "routeconfigurations"
  "genevetunnels"
  "networks"
  "ips"
  "namespacemaps"
  "firewallconfigurations"
  ####
  "nodes"
)

mkdir -p out/list

for res in "${RESOURCES[@]}"; do
  for cluster in "${!CLUSTERS[@]}"; do
    kubeconfig="${CLUSTERS[$cluster]}"
    echo "Saving ${cluster} ${res}..."
    if ! kubectl --kubeconfig "$kubeconfig" get "$res" -A > "out/list/${cluster}_${res}"; then
      echo "⚠️ Warning: failed to get ${cluster} ${res}" >&2
    fi
  done
done
done
