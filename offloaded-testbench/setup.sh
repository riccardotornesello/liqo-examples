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

MANIFEST_1="$here/manifests/resources_rome.yaml"
MANIFEST_2="$here/manifests/resources_milan.yaml"

MANIFEST_CALICO_1=https://raw.githubusercontent.com/projectcalico/calico/v3.30.3/manifests/operator-crds.yaml
MANIFEST_CALICO_2=https://raw.githubusercontent.com/projectcalico/calico/v3.30.3/manifests/tigera-operator.yaml
MANIFEST_CALICO_3="$here/manifests/calico.yaml"

LIQO_CLUSTER_CONFIG_YAML="$here/manifests/cluster.yaml"

# LIQO_REPO="https://github.com/liqotech/liqo"
# LIQO_VERSION="v1.0.1"

LIQO_REPO="https://github.com/Wekkser/liqo.git"
LIQO_VERSION="e300636af16a6ecd02aa661eb5c492243497f93a"

# LIQO_REPO="https://github.com/riccardotornesello/liqo.git"
# LIQO_VERSION="adc674974e54b9bb80d571db87a2eda380d4d8d6"

check_requirements

delete_all_kind_clusters

create_kind_cluster_no_wait "$CLUSTER_NAME_1" "$KUBECONFIG_1" "$LIQO_CLUSTER_CONFIG_YAML"
create_kind_cluster_no_wait "$CLUSTER_NAME_2" "$KUBECONFIG_2" "$LIQO_CLUSTER_CONFIG_YAML"

create_resources "$KUBECONFIG_1" "$MANIFEST_CALICO_1"
create_resources "$KUBECONFIG_1" "$MANIFEST_CALICO_2"
create_resources "$KUBECONFIG_1" "$MANIFEST_CALICO_3"

create_resources "$KUBECONFIG_2" "$MANIFEST_CALICO_1"
create_resources "$KUBECONFIG_2" "$MANIFEST_CALICO_2"
create_resources "$KUBECONFIG_2" "$MANIFEST_CALICO_3"

install_liqo_version "$CLUSTER_NAME_1" "$KUBECONFIG_1" "$LIQO_VERSION" "$LIQO_REPO"
install_liqo_version "$CLUSTER_NAME_2" "$KUBECONFIG_2" "$LIQO_VERSION" "$LIQO_REPO"

peer_clusters "$KUBECONFIG_1" "$KUBECONFIG_2"

create_namespace "$KUBECONFIG_1" rome-offloaded
create_namespace "$KUBECONFIG_1" rome-local
create_namespace "$KUBECONFIG_2" milan-local

offload_namespace "$KUBECONFIG_1" rome-offloaded

apply_resources "$KUBECONFIG_1" "$MANIFEST_1"
apply_resources "$KUBECONFIG_2" "$MANIFEST_2"
