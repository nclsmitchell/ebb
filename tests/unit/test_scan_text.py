from ebb.detect.scan_text import nearest_symbol


def test_finds_a_python_assignment_target() -> None:
    line = 'MODEL = "gpt-4o-mini"'
    match_start = line.index("gpt-4o-mini")
    assert nearest_symbol(line, match_start) == "MODEL"


def test_finds_a_json_key() -> None:
    line = '  "embedding_model": "text-embedding-3-large"'
    match_start = line.index("text-embedding")
    assert nearest_symbol(line, match_start) == "embedding_model"


def test_finds_a_yaml_key() -> None:
    line = "model: gemini-1.5-pro"
    match_start = line.index("gemini")
    assert nearest_symbol(line, match_start) == "model"


def test_finds_a_dockerfile_env_name() -> None:
    line = "ENV LEGACY_MODEL=gpt-3.5-turbo"
    match_start = line.index("gpt-3.5-turbo")
    assert nearest_symbol(line, match_start) == "LEGACY_MODEL"


def test_falls_back_to_the_line_prefix_when_theres_no_assignment() -> None:
    line = '    "claude-3-opus-20240229",'
    match_start = line.index("claude")
    symbol = nearest_symbol(line, match_start)
    assert symbol == line.strip()


def test_falls_back_to_unknown_for_a_blank_line() -> None:
    assert nearest_symbol("", 0) == "unknown"


def test_uses_the_nearest_assignment_not_the_first() -> None:
    line = "x = 1; MODEL = gpt-4o-mini"
    match_start = line.index("gpt-4o-mini")
    # Both "x =" and "MODEL =" match the assignment pattern in the prefix; the governing one is
    # the nearest (last) match before the model id, not the first one on the line.
    assert nearest_symbol(line, match_start) == "MODEL"
