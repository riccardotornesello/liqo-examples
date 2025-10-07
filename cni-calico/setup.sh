#!/bin/bash

set -e

here="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
# shellcheck source=/dev/null
source "$here/../../common.sh"
source "$here/../utils.sh"

CLUSTER_NAME=rome

KUBECONFIG=liqo_kubeconf_rome

LIQO_CLUSTER_CONFIG_YAML="$here/manifests/cluster.yaml"

MANIFEST_1=https://raw.githubusercontent.com/projectcalico/calico/v3.30.3/manifests/operator-crds.yaml
MANIFEST_2=https://raw.githubusercontent.com/projectcalico/calico/v3.30.3/manifests/tigera-operator.yaml
MANIFEST_3="$here/manifests/calico.yaml"
MANIFEST_4="$here/manifests/resources.yaml"

check_requirements

delete_all_kind_clusters

create_kind_cluster_no_wait "$CLUSTER_NAME" "$KUBECONFIG" "$LIQO_CLUSTER_CONFIG_YAML"

create_resources "$KUBECONFIG" "$MANIFEST_1"
create_resources "$KUBECONFIG" "$MANIFEST_2"
create_resources "$KUBECONFIG" "$MANIFEST_3"
apply_resources "$KUBECONFIG" "$MANIFEST_4"
