from pyqmd.chunking.scoring import BREAK_SCORES, score_line, BreakPoint


class TestBreakScores:
    def test_h1_has_highest_score(self):
        assert BREAK_SCORES["h1"] == 100

    def test_h2_lower_than_h1(self):
        assert BREAK_SCORES["h2"] < BREAK_SCORES["h1"]

    def test_code_block_end_higher_than_blank_line(self):
        assert BREAK_SCORES["code_block_end"] > BREAK_SCORES["blank_line"]


class TestScoreLine:
    def test_h1_heading(self):
        bp = score_line("# Hello World", prev_line="", in_code_block=False)
        assert bp is not None
        assert bp.score == BREAK_SCORES["h1"]
        assert bp.break_type == "h1"

    def test_h2_heading(self):
        bp = score_line("## Section Two", prev_line="", in_code_block=False)
        assert bp is not None
        assert bp.score == BREAK_SCORES["h2"]

    def test_h3_heading(self):
        bp = score_line("### Subsection", prev_line="", in_code_block=False)
        assert bp is not None
        assert bp.score == BREAK_SCORES["h3"]

    def test_h4_heading(self):
        bp = score_line("#### Deep heading", prev_line="", in_code_block=False)
        assert bp is not None
        assert bp.score == BREAK_SCORES["h4"]

    def test_blank_line(self):
        bp = score_line("", prev_line="Some text", in_code_block=False)
        assert bp is not None
        assert bp.score == BREAK_SCORES["blank_line"]

    def test_horizontal_rule(self):
        bp = score_line("---", prev_line="", in_code_block=False)
        assert bp is not None
        assert bp.score == BREAK_SCORES["hr"]

    def test_regular_text_returns_none(self):
        bp = score_line("Just regular text here.", prev_line="More text", in_code_block=False)
        assert bp is None

    def test_heading_inside_code_block_returns_none(self):
        bp = score_line("# This is a comment", prev_line="some code", in_code_block=True)
        assert bp is None

    def test_code_block_fence_end(self):
        bp = score_line("```", prev_line="print('hello')", in_code_block=True)
        assert bp is not None
        assert bp.score == BREAK_SCORES["code_block_end"]
