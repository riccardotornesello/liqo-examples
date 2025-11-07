#!/bin/bash

set -e

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"

KUBECONFIG="$here/../testbench/liqo_kubeconf_milan"
ROLE="provider"

BUILD_COMPONENTS=(crd-replicator fabric gateway ipam liqo-controller-manager liqoctl metric-agent proxy telemetry uninstaller virtual-kubelet webhook)

NAMESPACE="liqo"

declare -A DEPLOYMENTS
DEPLOYMENTS["liqo-crd-replicator"]="crd-replicator"
DEPLOYMENTS["liqo-ipam"]="ipam"
DEPLOYMENTS["liqo-metric-agent"]="metric-agent"
DEPLOYMENTS["liqo-proxy"]="proxy"
DEPLOYMENTS["liqo-webhook"]="webhook"
DEPLOYMENTS["liqo-controller-manager"]="liqo-controller-manager"

declare -A DAEMONSETS
DAEMONSETS["liqo-fabric"]="fabric"

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

# Update the image for each daemonset
for daemonset in "${!DAEMONSETS[@]}"; do
  component="${DAEMONSETS[$daemonset]}"

  # Extract the container name from the daemonset
  container_name=$(kubectl get daemonset --kubeconfig "$KUBECONFIG" "$daemonset" -n "$NAMESPACE" -o jsonpath='{.spec.template.spec.containers[0].name}')

  image_name="${DOCKER_REGISTRY}/${DOCKER_ORGANIZATION}/${component}-ci:${DOCKER_TAG}"

  echo "Updating daemonset: $daemonset, container: $container_name, image: $image_name"
  if ! kubectl --kubeconfig "$KUBECONFIG" set image "daemonset/$daemonset" "$container_name=$image_name" -n "$NAMESPACE"; then
    echo "Failed to update image for daemonset: $daemonset"
    exit 1
  fi
done

# Update the gateway
GATEWAY_IMAGE_NAME="${DOCKER_REGISTRY}/${DOCKER_ORGANIZATION}/gateway-ci:${DOCKER_TAG}"
if [ "$ROLE" == "provider" ]; then
  GATEWAY_TEMPLATE_NAME="wireguard-server"
  GATEWAY_TEMPLATE_RESOURCE="WgGatewayServerTemplate"

  GATEWAY_RESOURCE_NAMESPACE="liqo-tenant-rome"
  GATEWAY_RESOURCE_TYPE="wggatewayserver"
  GATEWAY_RESOURCE_NAME="rome"
else
  GATEWAY_TEMPLATE_NAME="wireguard-client"
  GATEWAY_TEMPLATE_RESOURCE="WgGatewayClientTemplate"

  GATEWAY_RESOURCE_NAMESPACE="liqo-tenant-milan"
  GATEWAY_RESOURCE_TYPE="wggatewayclient"
  GATEWAY_RESOURCE_NAME="milan"
fi

if ! kubectl --kubeconfig "$KUBECONFIG" patch $GATEWAY_TEMPLATE_RESOURCE $GATEWAY_TEMPLATE_NAME -n $NAMESPACE --type=json -p="[{\"op\": \"replace\", \"path\": \"/spec/template/spec/deployment/spec/template/spec/containers/0/image\", \"value\": \"$GATEWAY_IMAGE_NAME\"}]"; then
  echo "Failed to patch $GATEWAY_TEMPLATE_RESOURCE $GATEWAY_TEMPLATE_NAME"
  exit 1
fi

if ! kubectl --kubeconfig "$KUBECONFIG" delete $GATEWAY_RESOURCE_TYPE $GATEWAY_RESOURCE_NAME -n $GATEWAY_RESOURCE_NAMESPACE; then
  echo "Failed to delete $GATEWAY_RESOURCE_TYPE $GATEWAY_RESOURCE_NAME"
  exit 1
fi

echo "✅ All deployments updated successfully."
