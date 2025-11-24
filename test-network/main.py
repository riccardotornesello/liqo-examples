from input import parse_yaml
from clusters import load_clusters_from_config
from tests.execution import run_tests
from tests.context import TestManager
from tests.martrix import generate_test_matrix, generate_test_suite
from output import print_results


if __name__ == "__main__":
    config_data = parse_yaml("test.yaml")

    clusters = load_clusters_from_config(config_data.get("clusters", []))
    sources, destinations = generate_test_matrix(clusters)
    tests_suites = generate_test_suite(config_data.get("tests", []), clusters)

    for test_name, test_resources in tests_suites:
        with TestManager(test_name, test_resources):
            results = run_tests(sources, destinations, clusters)
            print_results(results, sources, destinations)
