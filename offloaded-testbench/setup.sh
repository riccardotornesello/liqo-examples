#!/bin/bash

set -e

here="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
# shellcheck source=/dev/null
source "$here/../../common.sh"
source "$here/../utils.sh"

CLUSTER_NAME_1=rome
CLUSTER_NAME_2=milan

KUBECONFIG_1=liqo_kubeconf_rome
KUBECONFIG_2=liqo_kubeconf_milan

MANIFEST_CONSUMER="$here/manifests/resources_consumer.yaml"
MANIFEST_PROVIDER="$here/manifests/resources_provider.yaml"
MANIFEST_OFFLOADED="$here/manifests/resources_offloaded.yaml"

MANIFEST_CALICO_1=https://raw.githubusercontent.com/projectcalico/calico/v3.30.3/manifests/operator-crds.yaml
MANIFEST_CALICO_2=https://raw.githubusercontent.com/projectcalico/calico/v3.30.3/manifests/tigera-operator.yaml
MANIFEST_CALICO_3="$here/manifests/calico.yaml"

REGISTRY_IP="172.18.0.2"

LIQO_CLUSTER_CONFIG_CONSUMER="$here/manifests/cluster_consumer.yaml"
LIQO_CLUSTER_CONFIG_PROVIDER="$here/manifests/cluster_provider.yaml"

# LIQO_REPO="https://github.com/liqotech/liqo"
# LIQO_VERSION="v1.0.1"

LIQO_REPO="https://github.com/Wekkser/liqo.git"
LIQO_VERSION="e300636af16a6ecd02aa661eb5c492243497f93a"

# LIQO_REPO="https://github.com/riccardotornesello/liqo.git"
# LIQO_VERSION="adc674974e54b9bb80d571db87a2eda380d4d8d6"

check_requirements

delete_all_kind_clusters

create_kind_cluster_no_wait "$CLUSTER_NAME_1" "$KUBECONFIG_1" "$LIQO_CLUSTER_CONFIG_CONSUMER"
create_kind_cluster_no_wait "$CLUSTER_NAME_2" "$KUBECONFIG_2" "$LIQO_CLUSTER_CONFIG_PROVIDER"

register_image_cache "$CLUSTER_NAME_1" "$REGISTRY_IP"
register_image_cache "$CLUSTER_NAME_2" "$REGISTRY_IP"

create_resources "$KUBECONFIG_1" "$MANIFEST_CALICO_1"
create_resources "$KUBECONFIG_1" "$MANIFEST_CALICO_2"
create_resources "$KUBECONFIG_1" "$MANIFEST_CALICO_3"

create_resources "$KUBECONFIG_2" "$MANIFEST_CALICO_1"
create_resources "$KUBECONFIG_2" "$MANIFEST_CALICO_2"
create_resources "$KUBECONFIG_2" "$MANIFEST_CALICO_3"

install_liqo_version "$CLUSTER_NAME_1" "$KUBECONFIG_1" "$LIQO_VERSION" "$LIQO_REPO"
install_liqo_version "$CLUSTER_NAME_2" "$KUBECONFIG_2" "$LIQO_VERSION" "$LIQO_REPO"

peer_clusters "$KUBECONFIG_1" "$KUBECONFIG_2"

create_namespace "$KUBECONFIG_1" offloaded
create_namespace "$KUBECONFIG_1" consumer-local
create_namespace "$KUBECONFIG_2" provider-local

offload_namespace "$KUBECONFIG_1" offloaded

apply_resources "$KUBECONFIG_1" "$MANIFEST_CONSUMER"
apply_resources "$KUBECONFIG_2" "$MANIFEST_PROVIDER"
apply_resources "$KUBECONFIG_1" "$MANIFEST_OFFLOADED"
