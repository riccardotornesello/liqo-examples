#!/bin/bash

set -e

here="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

COMPONENTS=(crd-replicator fabric gateway ipam liqo-controller-manager liqoctl metric-agent proxy telemetry uninstaller virtual-kubelet webhook)

# REGISTRY_NAME="liqo_tmp_registry"

# create_buildkitd_config() {
#   local ip_or_host="$1"
#   cat > buildkitd.toml <<EOF
# [registry."${ip_or_host}:5000"]
#   http = true
#   insecure = true
# EOF
# }

# recreate_buildx_builder() {
#   local builder_name="$1"
#   local buildkitd_config="$2"

#   # Remove builder if it exists
#   if docker buildx inspect "$builder_name" >/dev/null 2>&1; then
#     docker buildx rm "$builder_name"
#   fi

#   # Create a new builder and use it
#   docker buildx create --name "$builder_name" --use --config "$buildkitd_config"
# }

# # Remove the container if it already exists
# docker rm -f $REGISTRY_NAME 2>/dev/null || true

# # Start a Docker container with a local registry in the background
# container_id=$(docker run -d -p 5000:5000 --name $REGISTRY_NAME registry:2)
# docker network connect kind $container_id

# # Wait a few seconds to allow the container to start
# sleep 5

# # Find the IP address of the container
# container_ips=$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}|{{end}}' $container_id)
# container_public_ip=$(echo "$container_ips" | awk -F'|' '{print $1}')
# container_kind_ip=$(echo "$container_ips" | awk -F'|' '{print $2}')

# Set the environment variables
# export DOCKER_REGISTRY="$container_public_ip:5000"
# export DOCKER_TAG="local-$(date +%s)"
export DOCKER_REGISTRY="ttl.sh"
export ARCHS="linux/amd64"
export DOCKER_ORGANIZATION=$(uuidgen)
export DOCKER_TAG="1h"

# create_buildkitd_config "$container_public_ip"
# recreate_buildx_builder "mybuilder" "buildkitd.toml"

cd ../../../

# Run the build.sh script with the environment variable set
for component in "${COMPONENTS[@]}"; do
  echo "Building component: $component"
  ./build/liqo/build.sh "./cmd/$component/"
done

# Namespace e lista dei deployment da aggiornare
namespace="liqo"
deployments=(
  crd-replicator
  ipam
  metric-agent
  proxy
  webhook
  # TODO: contoller-manager
)

# Aggiornare l'immagine per ciascun deployment
for deployment in "${deployments[@]}"; do
  # Estrarre il nome del container dal deployment (primo container trovato)
  container_name=$(kubectl get deployment --kubeconfig ./examples/liqo-examples/quick-start/liqo_kubeconf_rome "liqo-$deployment" -n "$namespace" -o jsonpath='{.spec.template.spec.containers[0].name}')
  # image_name="${container_kind_ip}:5000/liqotech/${deployment}-ci:${DOCKER_TAG}"
  image_name="${DOCKER_REGISTRY}/${DOCKER_ORGANIZATION}/${deployment}-ci:${DOCKER_TAG}"

  echo "Aggiornamento immagine per il deployment $deployment: $image_name"
  if ! kubectl --kubeconfig ./examples/liqo-examples/quick-start/liqo_kubeconf_rome set image "deployment/liqo-$deployment" "$container_name=$image_name" -n "$namespace"; then
    echo "Errore durante l'aggiornamento del deployment $deployment"
    exit 1
  fi
done

echo "Aggiornamento completato per tutti i deployment nel namespace $namespace."