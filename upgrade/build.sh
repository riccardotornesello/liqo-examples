#!/bin/bash

# TODO: allow local registry

set -e

####################################################
# BUILD
####################################################

ALL_COMPONENTS=(
  liqo-controller-manager
  crd-replicator
  ipam
  metric-agent
  fabric
  gateway
  gateway/geneve
  gateway/wireguard
  proxy
  telemetry
  uninstaller
  virtual-kubelet
  webhook
)

# Set the environment variables for the build script
export DOCKER_REGISTRY="ttl.sh"
export ARCHS="linux/amd64"
export DOCKER_ORGANIZATION="riccardotornesello"
export DOCKER_TAG="3h"

rm -rf ../../../../liqo/bin

(
  cd ../../../../liqo

  # Build only the requested components
  for component in "${ALL_COMPONENTS[@]}"; do
    echo "Building component: $component"
    ./build/liqo/build.sh "./cmd/$component/"
  done
)
