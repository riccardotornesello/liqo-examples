from tabulate import tabulate
from tests import Test, TestEntity


def format_header_color(destination: TestEntity) -> str:
    destination_name = destination.name
    destination_cluster = destination.cluster_name

    color = "30"
    if destination_name.startswith("p"):
        if destination_cluster == "consumer":
            color = "43"
        else:
            color = "44"
    elif destination_name.startswith("s"):
        if destination_cluster == "consumer":
            color = "45"
        else:
            color = "46"

    return f"\x1b[{color}m {destination_name} \x1b[0m"


def get_result_cell(test_results: dict | None):
    if not test_results:
        return ""

    results_list = [test_results.get("curl"), test_results.get("ping")]
    return "".join([get_single_result_cell(result) for result in results_list])


def get_single_result_cell(result: bool | None):
    match result:
        case True:
            return "\x1b[42m Y \x1b[0m"
        case False:
            return "\x1b[41m N \x1b[0m"
        case _:
            return "   "


def get_formatted_results(
    results: dict,
    sources: list[TestEntity],
    destinations: list[TestEntity],
):
    return [
        [format_header_color(source)]
        + [
            get_result_cell(
                results.get(source.name, {})
                .get(destination.cluster_name, {})
                .get(destination.name)
            )
            for destination in destinations
        ]
        for source in sources
    ]


def print_results(
    tests: list[Test],
    sources: list[TestEntity],
    destinations: list[TestEntity],
):
    # For easier access, convert the results list into a nested dict.
    # Source name -> Destination cluster -> Destination name -> Test type -> Result

    results_dict: dict = {}
    for test in tests:
        src_name = test.src_name
        dst_name = test.dst_name
        dst_cluster_name = test.dst_cluster_name
        test_type = test.test_type

        if src_name not in results_dict:
            results_dict[src_name] = {}

        if dst_cluster_name not in results_dict[src_name]:
            results_dict[src_name][dst_cluster_name] = {}

        if dst_name not in results_dict[src_name][dst_cluster_name]:
            results_dict[src_name][dst_cluster_name][dst_name] = {}

        results_dict[src_name][dst_cluster_name][dst_name][test_type] = test.result

    header = ["source pod"] + [format_header_color(dest) for dest in destinations]
    rows = get_formatted_results(results_dict, sources, destinations)
    print(tabulate(rows, headers=header))
