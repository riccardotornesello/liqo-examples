#!/bin/bash

# TODO: allow local registry

set -e

####################################################
# ARGUMENT PARSING
####################################################

KUBECTL_KCFG=()

COMPONENTS_ARG=""
KUBECONFIG=""
UPDATE_CRD=1

while [[ $# -gt 0 ]]; do
  key="$1"
  case $key in
  --components)
    COMPONENTS_ARG="$2"
    shift # past argument
    shift # past value
    ;;
  --kubeconfig)
    KUBECONFIG="$2"
    shift # past argument
    shift # past value
    ;;
  --skip-crd)
    UPDATE_CRD=0
    shift # past argument
    ;;
  *)
    echo "Unknown option: $1"
    exit 1
    ;;
  esac
done

# If specified, filter the components
ALL_COMPONENTS=(crd-replicator fabric gateway ipam liqo-controller-manager liqoctl metric-agent proxy telemetry uninstaller virtual-kubelet webhook)
BUILD_COMPONENTS=("${ALL_COMPONENTS[@]}")
if [[ -n "$COMPONENTS_ARG" ]]; then
  IFS=',' read -ra REQ_COMPONENTS <<<"$COMPONENTS_ARG"
  BUILD_COMPONENTS=()
  for comp in "${REQ_COMPONENTS[@]}"; do
    comp_trimmed="$(echo "$comp" | xargs)"
    for c in "${ALL_COMPONENTS[@]}"; do
      if [[ "$c" == "$comp_trimmed" ]]; then
        BUILD_COMPONENTS+=("$c")
      fi
    done
  done
fi

# If the kubeconfig is specified, set the KUBECTL_KCFG variable
if [[ -n "$KUBECONFIG" ]]; then
  KUBECTL_KCFG=(--kubeconfig "$KUBECONFIG")
fi

####################################################
# CONFIGURATION
####################################################

LIQO_NAMESPACE="liqo"

declare -A DEPLOYMENTS
DEPLOYMENTS["liqo-crd-replicator"]="crd-replicator"
DEPLOYMENTS["liqo-ipam"]="ipam"
DEPLOYMENTS["liqo-metric-agent"]="metric-agent"
DEPLOYMENTS["liqo-proxy"]="proxy"
DEPLOYMENTS["liqo-webhook"]="webhook"
DEPLOYMENTS["liqo-controller-manager"]="liqo-controller-manager"

declare -A DAEMONSETS
DAEMONSETS["liqo-fabric"]="fabric"

####################################################
# BUILD
####################################################

# Set the environment variables for the build script
export DOCKER_REGISTRY="ttl.sh"
export ARCHS="linux/amd64"
export DOCKER_ORGANIZATION=$(uuidgen)
export DOCKER_TAG="1h"

(
  cd ../../../

  # Build only the requested components
  for component in "${BUILD_COMPONENTS[@]}"; do
    echo "Building component: $component"
    ./build/liqo/build.sh "./cmd/$component/"
  done
)

####################################################
# DEPLOYMENTS
####################################################

for deployment in "${!DEPLOYMENTS[@]}"; do
  component="${DEPLOYMENTS[$deployment]}"

  # Check if the component is in the build list
  skip=1
  for c in "${BUILD_COMPONENTS[@]}"; do
    if [[ "$component" == "$c" ]]; then
      skip=0
      break
    fi
  done
  if [[ $skip -eq 1 ]]; then
    continue
  fi

  # Extract the container name from the deployment
  container_name=$(kubectl "${KUBECTL_KCFG[@]}" get deployment "$deployment" -n "$LIQO_NAMESPACE" -o jsonpath='{.spec.template.spec.containers[0].name}')

  image_name="${DOCKER_REGISTRY}/${DOCKER_ORGANIZATION}/${component}-ci:${DOCKER_TAG}"

  echo "Updating deployment: $deployment, container: $container_name, image: $image_name"
  if ! kubectl "${KUBECTL_KCFG[@]}" set image "deployment/$deployment" "$container_name=$image_name" -n "$LIQO_NAMESPACE"; then
    echo "Failed to update image for deployment: $deployment"
    exit 1
  fi
done

####################################################
# DAEMONSETS
####################################################

for daemonset in "${!DAEMONSETS[@]}"; do
  component="${DAEMONSETS[$daemonset]}"

  # Check if the component is in the build list
  skip=1
  for c in "${BUILD_COMPONENTS[@]}"; do
    if [[ "$component" == "$c" ]]; then
      skip=0
      break
    fi
  done
  if [[ $skip -eq 1 ]]; then
    continue
  fi

  # Extract the container name from the daemonset
  container_name=$(kubectl "${KUBECTL_KCFG[@]}" get daemonset "$daemonset" -n "$LIQO_NAMESPACE" -o jsonpath='{.spec.template.spec.containers[0].name}')

  image_name="${DOCKER_REGISTRY}/${DOCKER_ORGANIZATION}/${component}-ci:${DOCKER_TAG}"

  # If the daemonset is liqo-fabric, change the command to /usr/bin/fabric
  if [[ "$daemonset" == "liqo-fabric" ]]; then
    if ! kubectl "${KUBECTL_KCFG[@]}" patch daemonset "$daemonset" -n "$LIQO_NAMESPACE" --type=json -p='[{"op": "replace", "path": "/spec/template/spec/containers/0/command", "value": ["/usr/bin/fabric"]}]'; then
      echo "Failed to patch command for daemonset: $daemonset"
      exit 1
    fi
  fi

  # Update the image
  echo "Updating daemonset: $daemonset, container: $container_name, image: $image_name"
  if ! kubectl "${KUBECTL_KCFG[@]}" set image "daemonset/$daemonset" "$container_name=$image_name" -n "$LIQO_NAMESPACE"; then
    echo "Failed to update image for daemonset: $daemonset"
    exit 1
  fi
done

####################################################
# GATEWAY
####################################################

# Check if gateway needs to be updated
update_gateway=0
for c in "${BUILD_COMPONENTS[@]}"; do
  if [[ "$c" == "gateway" ]]; then
    update_gateway=1
    break
  fi
done

if [[ $update_gateway -eq 1 ]]; then
  GATEWAY_IMAGE_NAME="${DOCKER_REGISTRY}/${DOCKER_ORGANIZATION}/gateway-ci:${DOCKER_TAG}"

  # Patch both WgGatewayServerTemplate and WgGatewayClientTemplate
  for template in "wireguard-server WgGatewayServerTemplate" "wireguard-client WgGatewayClientTemplate"; do
    set -- $template
    TEMPLATE_NAME=$1
    TEMPLATE_RESOURCE=$2
    if ! kubectl "${KUBECTL_KCFG[@]}" patch $TEMPLATE_RESOURCE $TEMPLATE_NAME -n $LIQO_NAMESPACE --type=json -p="[{\"op\": \"replace\", \"path\": \"/spec/template/spec/deployment/spec/template/spec/containers/0/image\", \"value\": \"$GATEWAY_IMAGE_NAME\"}]"; then
      echo "Failed to patch $TEMPLATE_RESOURCE $TEMPLATE_NAME"
      exit 1
    fi
  done

  # Delete all WgGatewayServer and WgGatewayClient resources in namespaces starting with liqo-tenant-
  namespaces=$(kubectl "${KUBECTL_KCFG[@]}" get ns -o jsonpath='{.items[*].metadata.name}' | tr ' ' '\n' | grep '^liqo-tenant-')
  for ns in $namespaces; do
    for resource in wggatewayserver wggatewayclient; do
      resources=$(kubectl "${KUBECTL_KCFG[@]}" get $resource -n $ns --no-headers --ignore-not-found | awk '{print $1}')
      for r in $resources; do
        if ! kubectl "${KUBECTL_KCFG[@]}" delete $resource $r -n $ns; then
          echo "Failed to delete $resource $r in namespace $ns"
          exit 1
        fi
      done
    done
  done
fi

####################################################
# CRD
####################################################

if [[ $UPDATE_CRD -eq 1 ]]; then
  echo "Applying CRDs..."
  if ! kubectl "${KUBECTL_KCFG[@]}" apply -f ../../../deployments/liqo/charts/liqo-crds/crds/; then
    echo "Failed to apply CRDs"
    exit 1
  fi
fi


echo "✅ All deployments updated successfully."
