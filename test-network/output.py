from tabulate import tabulate
from tests.execution import Test, TestEntity


def format_header_color(destination: TestEntity) -> str:
    """
    Formats a destination entity name with ANSI color codes for terminal display.
    Colors are assigned based on the entity's color field.

    Args:
        destination (TestEntity): The destination entity to format.

    Returns:
        str: The entity name wrapped with ANSI color codes.
    """
    name = destination.name
    color = destination.color

    if not color:
        return f" {name} "

    else:
        return f"\x1b[{color}m {name} \x1b[0m"


def get_result_cell(test_results: dict | None) -> str:
    """
    Formats test results for a single source-destination pair into a cell string.

    Combines curl and ping test results into a single formatted string.

    Args:
        test_results (dict | None): Dictionary containing test results with "curl" and "ping" keys.

    Returns:
        str: Formatted string with colored result indicators for each test type.
    """
    if not test_results:
        return ""

    results_list = [test_results.get("curl"), test_results.get("ping")]
    return "".join([get_single_result_cell(result) for result in results_list])


def get_single_result_cell(result: bool | None) -> str:
    """
    Formats a single test result with ANSI color codes.

    Args:
        result (bool | None): The test result - True for success, False for failure, None for not run.

    Returns:
        str: Formatted string with color:
            - Green background with "Y" for True
            - Red background with "N" for False
            - Three spaces for None
    """
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
) -> list[list[str]]:
    """
    Formats test results into a 2D list for tabular display.

    Creates a matrix where each row represents a source entity and each column
    represents a destination entity, with formatted test results in each cell.

    Args:
        results (dict): Nested dictionary of test results organized by
            source name -> destination cluster -> destination name -> test type -> result.
        sources (list[TestEntity]): List of source entities.
        destinations (list[TestEntity]): List of destination entities.

    Returns:
        list[list[str]]: 2D list where each row starts with the formatted source name
            followed by formatted result cells for each destination.
    """
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


def print_test_summary(tests: list[Test]) -> None:
    """
    Prints a summary of test results to the console.
    For each test, it displays the source, destination, test type, and result.

    Args:
        tests (list[Test]): List of test objects containing test results.
    """
    for test in tests:
        color = "\x1b[32m" if test.result else "\x1b[31m"
        result_str = "SUCCESS" if test.result else "FAILURE"
        result_str = f"{color}{result_str}\x1b[0m"

        print(
            f"{test.src_name} ({test.src_ip}) -> {test.dst_name} ({test.dst_ip}) | {test.test_type}: {result_str}"
        )


def print_results(
    tests: list[Test],
    sources: list[TestEntity],
    destinations: list[TestEntity],
    verbose: bool = False,
) -> None:
    """
    Prints test results in a formatted table to the console.

    Converts a list of test objects into a nested dictionary structure, then
    formats and prints the results as a colored table with sources as rows
    and destinations as columns.

    Args:
        tests (list[Test]): List of test objects containing test results.
        sources (list[TestEntity]): List of source entities (rows in the table).
        destinations (list[TestEntity]): List of destination entities (columns in the table).
        verbose (bool, optional): If True, prints a detailed summary of each test. Defaults to False.

    Returns:
        None: Results are printed to stdout.
    """
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

    if verbose:
        print_test_summary(tests)

    header = ["source pod"] + [format_header_color(dest) for dest in destinations]
    rows = get_formatted_results(results_dict, sources, destinations)
    print(tabulate(rows, headers=header))
