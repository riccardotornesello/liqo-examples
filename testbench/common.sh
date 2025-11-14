#!/bin/bash

set -e           # Fail in case of error
set -o nounset   # Fail if undefined variables are used
set -o pipefail  # Fail if one of the piped commands fails

function setup_colors() {
    # Only use colors if connected to a terminal
    if [ -t 1 ]; then
        RED=$(printf '\033[31m')
        GREEN=$(printf '\033[32m')
        YELLOW=$(printf '\033[33m')
        BLUE=$(printf '\033[34m')
        BOLD=$(printf '\033[1m')
        RESET=$(printf '\033[m')
        PREVIOUS_LINE=$(printf '\e[1A')
        CLEAR_LINE=$(printf '\e[K')
    else
        RED=""
        GREEN=""
        YELLOW=""
        BLUE=""
        BOLD=""
        RESET=""
        PREVIOUS_LINE=""
        CLEAR_LINE=""
    fi
}

function error() {
    echo -e "${RED}${BOLD}ERROR${RESET}\t$1"
}

function warning() {
    echo -e "${YELLOW}${BOLD}WARN${RESET}\t$1"
}

function info() {
    echo -e "${BLUE}${BOLD}INFO${RESET}\t$1"
}

function success_clear_line() {
    echo -e "${PREVIOUS_LINE}${CLEAR_LINE}${GREEN}${BOLD}SUCCESS${RESET}\t$1"
}

function success() {
    echo -e "${GREEN}${BOLD}SUCCESS${RESET}\t$1"
}

function check_requirements() {
    if ! command -v docker &> /dev/null;
    then
        error "Docker engine could not be found on your system. Please install docker engine to continue: https://docs.docker.com/get-docker/"
        exit 1
    fi

    if ! docker info &> /dev/null;
    then
        error "Docker is not running. Please start it to continue."
        exit 1
    fi

    if ! command -v kubectl &> /dev/null;
    then
        error "Kubectl could not be found on your system. Please install kubectl to continue: https://kubernetes.io/docs/tasks/tools/#kubectl"
        exit 1
    fi

    if ! command -v liqoctl &> /dev/null;
    then
        error "Liqoctl could not be found on your system. Please install liqoctl to continue"
        exit 1
    fi

    # check for extra requirements
    for cmd in "$@"; do
        if ! command -v "$cmd" &> /dev/null;
        then
            error "Command $cmd could not be found on your system. Please install it to continue."
            exit 1
        fi
    done
}

function delete_clusters() {
    for cluster in "$@"; do
        info "Ensuring that no cluster \"$cluster\" is running..."
        kind delete cluster --name "$cluster" > /dev/null 2>&1
        success_clear_line "No cluster \"${cluster}\" is running."
    done
}

function create_kind_cluster() {
    local name="$1"
    local kubeconfig="$2"
    local config="$3"

    info "Creating cluster \"$name\"..."
    fail_on_error "kind create cluster --name $name \
        --kubeconfig $kubeconfig --config $config --wait 5m" "Failed to create cluster \"$name\""
    success_clear_line "Cluster \"$name\" has been created."
}

function install_liqo_kind() {
    local cluster_name="$1"
    local kubeconfig="$2"
    local commit_sha="${3:-}"
	local repo_url="${4:-}"

    info "Installing liqo on cluster \"$cluster_name\"..."

    shift 4
    labels="$*"

    fail_on_error "liqoctl install kind --cluster-id $cluster_name \
        --cluster-labels=$(join_by , "${labels[@]}") \
        --kubeconfig $kubeconfig \
        --version $commit_sha \
        --repo-url $repo_url" "Failed to install liqo on cluster \"$cluster_name\""

    success_clear_line "Liqo has been installed on cluster \"$cluster_name\"."
}

function install_liqo_k3d() {
    local cluster_name="$1"
    local kubeconfig="$2"
    local pod_cidr="$3"
    local service_cidr="$4"
    local repo_url="${5:-}"
	local commit_sha="${6:-}"
	local values_file="${7:-}"

    if [ -z "$pod_cidr" ]; then
        pod_cidr="10.42.0.0/16"
    fi
    if [ -z "$service_cidr" ]; then
        service_cidr="10.43.0.0/16"
    fi

    # Set the --repo-url, --version, and --values arguments if provided
	arguments=()
	if [ -n "$repo_url" ]; then
		arguments+=("--repo-url $repo_url")
	fi
	if [ -n "$commit_sha" ]; then
		arguments+=("--version $commit_sha")
	fi
	if [ -n "$values_file" ]; then
		arguments+=("--values $values_file")
	fi
    arguments_string=$(join_by " " "${arguments[@]}")

    info "Installing liqo on cluster \"$cluster_name\"..."

    shift 7
    labels="$*"

    api_server_address=$(kubectl get nodes --kubeconfig "$kubeconfig" --selector=node-role.kubernetes.io/master -o jsonpath='{$.items[*].status.addresses[?(@.type=="InternalIP")].address}')

    fail_on_error "liqoctl install k3s --cluster-id $cluster_name \
        --cluster-labels=$(join_by , "${labels[@]}") \
        --pod-cidr $pod_cidr \
        --service-cidr $service_cidr \
        --api-server-url https://$api_server_address:6443 \
        --kubeconfig $kubeconfig \
        ${arguments_string}" "Failed to install liqo on cluster \"${cluster_name}\""

    success_clear_line "Liqo has been installed on cluster \"$cluster_name\"."
}

function delete_k3d_clusters() {
    for cluster in "$@"; do
        info "Ensuring that no cluster \"$cluster\" is running..."
        k3d cluster delete "$cluster" > /dev/null 2>&1
        success_clear_line "No cluster \"${cluster}\" is running."
    done
}

function create_k3d_cluster() {
    local name="$1"
    local config="$2"

    shift 2
	options="$*"
	options_string=$(join_by " " "${options[@]}")

    info "Creating cluster \"$name\"..."
    fail_on_error "k3d cluster create -c $config --kubeconfig-update-default=false $options_string" "Failure to create cluster \"${name}\""
    success_clear_line "Cluster \"$name\" has been created."
}

function get_k3d_kubeconfig() {
    local name="$1"

    k3d kubeconfig write "$name"
}

function install_k8gb() {
    local kubeconfig="$1"
    local cluster_geo_tag="$2"
    local cluster_ext_geo_tag="$3"
    local dns_ip="$4"

    info "Installing k8gb on cluster..."

    fail_on_error "kubectl create namespace k8gb --kubeconfig $kubeconfig" "Failed to create namespace k8gb"
    fail_on_error "kubectl -n k8gb create secret generic rfc2136 --kubeconfig $kubeconfig --from-literal=secret=96Ah/a2g0/nLeFGK+d/0tzQcccf9hCEIy34PoXX2Qg8=" "Failed to create secret"

    fail_on_error "helm -n k8gb upgrade -i k8gb k8gb/k8gb --kubeconfig $kubeconfig \
        --set k8gb.clusterGeoTag=$cluster_geo_tag \
        --set k8gb.extGslbClustersGeoTags=$cluster_ext_geo_tag \
        --set k8gb.reconcileRequeueSeconds=10 \
        --set k8gb.dnsZoneNegTTL=10 \
        --set k8gb.imageTag=v0.9.0 \
        --set k8gb.log.format=simple \
        --set k8gb.log.level=debug \
        --set rfc2136.enabled=true \
        --set k8gb.edgeDNSServers[0]=${dns_ip}:30053 \
        --set externaldns.image=absaoss/external-dns:rfc-ns1 \
        --wait --timeout=2m0s" "Failed to install k8gb"

    success_clear_line "K8gb has been installed on cluster."
}

function install_ingress_nginx() {
    local kubeconfig="$1"
    local namespace="$2"
    local values="$3"
    local version="$4"

    if [ -z "$version" ]; then
        version="4.0.15"
    fi

    info "Installing ingress-nginx on cluster..."

    fail_on_error "helm -n $namespace upgrade --kubeconfig $kubeconfig -i nginx-ingress nginx-stable/ingress-nginx \
	    --version $version -f $values" "Failed to install ingress-nginx"

    success_clear_line "Ingress-nginx has been installed on cluster."
}

function fail_on_error() {
    local cmd="$1"
    local msg="$2"

    set +e
    output=$($cmd 2>&1)
    # shellcheck disable=SC2181
    # we need to collect the output and then check the exit code
    if [ $? -ne 0 ]; then
        error "$msg: ${output}"
        exit 1
    fi
    set -e
}

function join_by() {
    local IFS="$1"
    shift
    echo "$*"
}

function apply_resources() {
	local kubeconfig="$1"
	local manifest="$2"

	info "Applying manifest \"$manifest\"..."

	fail_on_error "kubectl apply -f $manifest --kubeconfig $kubeconfig" "Failed to apply resources from manifest \"$manifest\""

	success_clear_line "Manifest \"$manifest\" applied successfully."
}

function create_resources() {
	local kubeconfig="$1"
	local manifest="$2"

	info "Creating resources from manifest \"$manifest\"..."

	fail_on_error "kubectl create -f $manifest --kubeconfig $kubeconfig" "Failed to create resources from manifest \"$manifest\""

	success_clear_line "Resources from manifest \"$manifest\" created successfully."
}

function create_namespace() {
	local kubeconfig="$1"
	local name="$2"

	info "Creating namespace \"$name\"..."

	fail_on_error "kubectl create namespace $name --kubeconfig $kubeconfig" "Failed to create namespace \"$name\""

	success_clear_line "Namespace \"$name\" created successfully."
}

function peer_clusters() {
	local kubeconfig="$1"
	local remote_kubeconfig="$2"
	local gw_server_service_type="${3-}"
	local server_ip="${4-}"

	arguments=()
	if [ -n "$gw_server_service_type" ]; then
		arguments+=("--gw-server-service-type $gw_server_service_type")
	fi
	if [ -n "$server_ip" ]; then
		arguments+=("--gw-server-service-loadbalancerip $server_ip")
	fi
    arguments_string=$(join_by " " "${arguments[@]}")

	info "Peering clusters..."

	fail_on_error "liqoctl peer \
        --kubeconfig $kubeconfig \
        --remote-kubeconfig $remote_kubeconfig \
        ${arguments_string}" "Failed to peer clusters"

	success_clear_line "Clusters have been peered."
}

function offload_namespace() {
	local kubeconfig="$1"
	local name="$2"

	info "Offloading namespace \"$name\"..."

	fail_on_error "liqoctl offload namespace $name --kubeconfig $kubeconfig" "Failed to offload namespace \"$name\""

	success_clear_line "Namespace \"$name\" offloaded successfully."
}

function get_container_ip() {
	local container_name="$1"
	local network_name="${2:-bridge}"

	container_ip=$(docker inspect -f "{{index .NetworkSettings.Networks \"${network_name}\" \"IPAddress\"}}" "$container_name")

	echo "$container_ip"
}

function install_cilium() {
	local kubeconfig="$1"
	local values_file="$2"
	local version="${3:-1.18.2}"

	info "Installing Cilium..."

	fail_on_error "cilium install --kubeconfig $kubeconfig --version $version --values $values_file" "Failed to install Cilium"

	success_clear_line "Cilium has been installed."
}

function install_calico() {
	local kubeconfig="$1"
	local values_file="$2"
	local version="${3:-3.30.3}"

	info "Installing Calico..."

	create_resources "$kubeconfig" "https://raw.githubusercontent.com/projectcalico/calico/v${version}/manifests/operator-crds.yaml"
    create_resources "$kubeconfig" "https://raw.githubusercontent.com/projectcalico/calico/v${version}/manifests/tigera-operator.yaml"
    create_resources "$kubeconfig" "$values_file"

	success_clear_line "Calico has been installed."
}

function create_docker_network() {
	local network_name="$1"

	info "Creating docker network \"$network_name\"..."

	if [ "$(docker network ls -q -f name=^${network_name}$)" ]; then
		success_clear_line "Docker network \"$network_name\" already exists."
		return
	fi

	fail_on_error "docker network create $network_name" "Failed to create docker network \"$network_name\""

	success_clear_line "Docker network \"$network_name\" created."
}

setup_colors
