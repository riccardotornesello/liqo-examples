from tabulate import tabulate


def format_header_color(destination):
    destination_name = destination["name"]
    destination_cluster = destination["cluster"]

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


def get_result_cell(test_results):
    if not test_results:
        return ""

    if test_results.destination["type"] == "service":
        result = test_results.get_result("curl")
        match result:
            case True:
                return "\x1b[42m  Y  \x1b[0m"
            case False:
                return "\x1b[41m  N  \x1b[0m"
            case _:
                return ""
    else:
        curl_result = test_results.get_result("curl")
        ping_result = test_results.get_result("ping")

        output = ""

        match curl_result:
            case True:
                output += "\x1b[42m Y \x1b[0m"
            case False:
                output += "\x1b[41m N \x1b[0m"
            case _:
                output += "   "
        match ping_result:
            case True:
                output += "\x1b[42m Y \x1b[0m"
            case False:
                output += "\x1b[41m N \x1b[0m"
            case _:
                output += "   "

        return output


def get_formatted_results(results, sources, destinations):
    return [
        [format_header_color(source)]
        + [
            get_result_cell(
                results[source["name"]]
                .get(destination["namespace"], {})
                .get(destination["name"])
            )
            for destination in destinations
        ]
        for source in sources
    ]


def print_results(results, sources, destinations):
    header = ["source pod"] + [format_header_color(dest) for dest in destinations]
    rows = get_formatted_results(results, sources, destinations)
    print(tabulate(rows, headers=header))
