"""Shared reporting helpers for review analysis scripts."""


def print_top_issues(top_issues, header, count_format, examples_label):
    """Print the top-N issue summary."""
    print(f"\n{header}\n")
    for i, issue in enumerate(top_issues, 1):
        print(f"{i}. {issue['category'].replace('_', ' ').title()}")
        print(count_format.format(count=issue['count'], percentage=issue['percentage']))
        print(examples_label)
        for example in issue['examples']:
            print(f"   - {example}")
        print()


def print_emerging_issues(
    emerging_issues,
    header,
    empty_message,
    increase_format,
    comparison_format,
):
    """Print emerging issue summary, or a fallback message if none exist."""
    if emerging_issues:
        print(f"\n{header}\n")
        for i, issue in enumerate(emerging_issues, 1):
            print(f"{i}. {issue['category'].replace('_', ' ').title()}")
            print(increase_format.format(increase_rate=issue['increase_rate']))
            print(comparison_format.format(
                comparison_count=issue['comparison_count'],
                recent_count=issue['recent_count']
            ))
            print()
    else:
        print(f"\n{empty_message}")
