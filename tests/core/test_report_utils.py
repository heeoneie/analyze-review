from core.report_utils import print_top_issues, print_emerging_issues


class TestPrintTopIssues:
    def test_prints_all_issues(self, sample_top_issues, capsys):
        print_top_issues(
            sample_top_issues,
            header="=== Top Issues ===",
            count_format="   Count: {count} ({percentage}%)",
            examples_label="   Examples:",
        )
        output = capsys.readouterr().out
        assert "Delivery Delay" in output
        assert "Poor Quality" in output
        assert "Wrong Item" in output

    def test_prints_count_and_percentage(self, sample_top_issues, capsys):
        print_top_issues(
            sample_top_issues,
            header="Header",
            count_format="   Count: {count} ({percentage}%)",
            examples_label="   Examples:",
        )
        output = capsys.readouterr().out
        assert "4" in output
        assert "40.0" in output

    def test_prints_examples(self, sample_top_issues, capsys):
        print_top_issues(
            sample_top_issues,
            header="Header",
            count_format="   {count}",
            examples_label="   Examples:",
        )
        output = capsys.readouterr().out
        assert "Late" in output
        assert "Slow" in output


class TestPrintEmergingIssues:
    def test_prints_issues_when_present(self, sample_emerging_issues, capsys):
        print_emerging_issues(
            sample_emerging_issues,
            header="=== Emerging ===",
            empty_message="No emerging issues",
            increase_format="   Increase: {increase_rate}%",
            comparison_format="   {comparison_count} → {recent_count}",
        )
        output = capsys.readouterr().out
        assert "Missing Parts" in output
        assert "400.0" in output

    def test_prints_empty_message_when_none(self, capsys):
        print_emerging_issues(
            [],
            header="Header",
            empty_message="특이사항 없음",
            increase_format="",
            comparison_format="",
        )
        output = capsys.readouterr().out
        assert "특이사항 없음" in output
