function delete_all_kind_clusters() {
    info "Deleting all kind clusters..."

    clusters=$(kind get clusters)

    if [ -z "$clusters" ]; then
        success_clear_line "No kind clusters found."
        return 0
    fi

    for cluster in $clusters; do
        kind delete cluster --name "$cluster" > /dev/null 2>&1
    done

    success_clear_line "All kind clusters have been deleted."
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

function create_kind_cluster_no_wait() {
    local name="$1"
    local kubeconfig="$2"
    local config="$3"

    info "Creating cluster \"$name\"..."
    fail_on_error "kind create cluster --name $name \
        --kubeconfig $kubeconfig --config $config" "Failed to create cluster \"$name\""
    success_clear_line "Cluster \"$name\" has been created."
}

function peer_clusters() {
    local kubeconfig="$1"
    local remote_kubeconfig="$2"

    info "Peering clusters..."

    fail_on_error "liqoctl peer \
        --kubeconfig $kubeconfig \
        --remote-kubeconfig $remote_kubeconfig \
        --gw-server-service-type NodePort" "Failed to peer clusters"

    success_clear_line "Clusters have been peered."
}

function create_namespace() {
    local kubeconfig="$1"
    local name="$2"

    info "Creating namespace \"$name\"..."

    fail_on_error "kubectl create namespace $name --kubeconfig $kubeconfig" "Failed to create namespace \"$name\""

    success_clear_line "Namespace \"$name\" created successfully."
}

function offload_namespace() {
    local kubeconfig="$1"
    local name="$2"

    info "Offloading namespace \"$name\"..."

    fail_on_error "liqoctl offload namespace $name --kubeconfig $kubeconfig" "Failed to offload namespace \"$name\""

    success_clear_line "Namespace \"$name\" offloaded successfully."
}

function install_liqo_version() {
    local cluster_name="$1"
    local kubeconfig="$2"
    local commit_sha="$3"
    local repo_url="$4"

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

function wait_for_nodes_ready() {
    local kubeconfig="$1"
    local timeout="${2:-300}"  # Default 5 minutes timeout
    local interval="${3:-5}"   # Default 5 seconds interval

    info "Waiting for all nodes to be ready..."

    local elapsed=0
    while [ $elapsed -lt $timeout ]; do
        local not_ready_nodes=$(kubectl get nodes --kubeconfig "$kubeconfig" --no-headers 2>/dev/null | grep -v " Ready " | wc -l)

        if [ "$not_ready_nodes" -eq 0 ]; then
            success_clear_line "All nodes are ready."
            return 0
        fi

        sleep $interval
        elapsed=$((elapsed + interval))
    done

    error "Timeout waiting for nodes to be ready after ${timeout}s"
    return 1
}

function register_image_cache() {
    local cluster_name="$1"
    local registry_ip="$2"

    local setup_url="http://$registry_ip:3128/setup/systemd"
    
    curl -s "$setup_url" | sed "s/docker\.service/containerd\.service/g" | sed "/Environment/ s/$/ \"NO_PROXY=127.0.0.0\/8,10.0.0.0\/8,172.16.0.0\/12,192.168.0.0\/16\"/" > /tmp/setup_cache.sh

    info "Registering image cache for cluster \"$cluster_name\"..."

    for NODE in $(kind get nodes --name "$cluster_name"); do
        fail_on_error "docker cp /tmp/setup_cache.sh $NODE:/setup_cache.sh" "Failed to copy setup script to node \"$NODE\" in cluster \"$cluster_name\""
        fail_on_error "docker exec $NODE bash /setup_cache.sh" "Failed to register image cache for node \"$NODE\" in cluster \"$cluster_name\""
    done

    success_clear_line "Image cache registered for cluster \"$cluster_name\"."
}
