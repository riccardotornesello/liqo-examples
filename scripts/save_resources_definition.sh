#!/bin/bash

# This script saves the definition of Liqo resources from both consumer and provider clusters.
# It retrieves the resources and saves the definition of the first found resource of each type to a file.
# The output files are named according to the cluster and resource type (e.g., consumer_gatewayclients.yaml) and stored in the out/definition directory.

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
)

mkdir -p out/definition

for cluster in "${!CLUSTERS[@]}"; do
  kubeconfig="${CLUSTERS[$cluster]}"

  for resource in "${RESOURCES[@]}"; do
    resources=$(kubectl --kubeconfig="$kubeconfig" get "$resource" --all-namespaces -o jsonpath='{range .items[*]}{.metadata.namespace}/{.metadata.name}{"\n"}{end}')

    count=$(echo "$resources" | grep -v '^$' | wc -l)

    if [[ $count -ge 1 ]]; then
      first_resource=$(echo "$resources" | head -n 1)
      ns=$(echo "$first_resource" | cut -d'/' -f1)
      name=$(echo "$first_resource" | cut -d'/' -f2)

      outfile="out/definition/${cluster}_${resource}.yaml"
      echo "✅ Found $count resources for $resource on $cluster -> saving: $ns/$name in $outfile"

      kubectl --kubeconfig="$kubeconfig" get "$resource" "$name" -n "$ns" -o yaml > "$outfile"
    else
      echo "⚠️ No resource found for $resource on $cluster"
    fi
  done
done
