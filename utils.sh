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
