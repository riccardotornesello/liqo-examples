#!/bin/bash

set -e

here="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

KUBECONFIG="$here/../quick-start/liqo_kubeconf_rome"

BUILD_COMPONENTS=(crd-replicator fabric gateway ipam liqo-controller-manager liqoctl metric-agent proxy telemetry uninstaller virtual-kubelet webhook)

NAMESPACE="liqo"

declare -A DEPLOYMENTS
DEPLOYMENTS["liqo-crd-replicator"]="crd-replicator"
DEPLOYMENTS["liqo-ipam"]="ipam"
DEPLOYMENTS["liqo-metric-agent"]="metric-agent"
DEPLOYMENTS["liqo-proxy"]="proxy"
DEPLOYMENTS["liqo-webhook"]="webhook"
DEPLOYMENTS["liqo-controller-manager"]="liqo-controller-manager"


# Set the environment variables for the build script
export DOCKER_REGISTRY="ttl.sh"
export ARCHS="linux/amd64"
export DOCKER_ORGANIZATION=$(uuidgen)
export DOCKER_TAG="1h"

cd ../../../

# Run the build.sh script with the environment variable set
for component in "${BUILD_COMPONENTS[@]}"; do
  echo "Building component: $component"
  ./build/liqo/build.sh "./cmd/$component/"
done

# Update the image for each deployment
for deployment in "${!DEPLOYMENTS[@]}"; do
  component="${DEPLOYMENTS[$deployment]}"

  # Extract the container name from the deployment
  container_name=$(kubectl get deployment --kubeconfig "$KUBECONFIG" "$deployment" -n "$NAMESPACE" -o jsonpath='{.spec.template.spec.containers[0].name}')
  
  image_name="${DOCKER_REGISTRY}/${DOCKER_ORGANIZATION}/${component}-ci:${DOCKER_TAG}"

  echo "Updating deployment: $deployment, container: $container_name, image: $image_name"
  if ! kubectl --kubeconfig "$KUBECONFIG" set image "deployment/$deployment" "$container_name=$image_name" -n "$NAMESPACE"; then
    echo "Failed to update image for deployment: $deployment"
    exit 1
  fi
done

echo "✅ All deployments updated successfully."
