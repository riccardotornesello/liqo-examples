#!/usr/bin/env bash

# This script exports all resources of a given type from all namespaces in a Kubernetes cluster.
# It saves each resource in a separate YAML file named <namespace>__<name>.yaml
# inside the directory out/export-<resource>-export.

# Usage: ./export-all.sh <resource_type> <kubeconfig>
# Example: ./export-all.sh deployment liqo_kubeconf_rome

RESOURCE="$1"
KUBECONFIG="$2"

OUTDIR="out/export-${RESOURCE}-export"

mkdir -p "$OUTDIR"

kubectl --kubeconfig "$KUBECONFIG" get "$RESOURCE" -A -o custom-columns="NAMESPACE:.metadata.namespace,NAME:.metadata.name" --no-headers | while read -r NAMESPACE NAME; do
    FILE="${OUTDIR}/${NAMESPACE}__${NAME}.yaml"
    echo "Exporting $RESOURCE $NAMESPACE/$NAME in $FILE"
    kubectl --kubeconfig "$KUBECONFIG" get "$RESOURCE" -n "$NAMESPACE" "$NAME" -o yaml > "$FILE"
done
