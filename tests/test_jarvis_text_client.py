"""Read-only text entry point and Streamlit interaction regression tests."""
import copy
import json
from unittest.mock import patch

import pytest
from streamlit.testing.v1 import AppTest

from jarvis.adapter import JarvisCommandError
from jarvis.text_client import answer_question
from tests.test_jarvis_api import fixture_snapshot


def test_questions_keep_snapshot_unchanged_and_disable_research():
    snapshot = fixture_snapshot()
    before = copy.deepcopy(snapshot)
    with patch("jarvis.text_client.load_snapshot", return_value=snapshot), patch(
        "jarvis.text_client.execute_command", return_value={"message": "ok"}
    ) as execute:
        answer_question("Analyser FRO")
    assert execute.call_args.kwargs["research_loader"] is None
    assert snapshot == before


def test_actual_adapter_answers_brief_and_stock_without_research(tmp_path, monkeypatch):
    path = tmp_path / "snapshot.json"
    path.write_text(json.dumps(fixture_snapshot()), encoding="utf-8")
    monkeypatch.setenv("INVESTMENT_OS_SNAPSHOT", str(path))
    before = path.read_bytes()
    brief = answer_question("Hvordan er status på min portefølje?")
    stock = answer_question("Analyser FRO")
    assert brief["intent"] == "investment_brief"
    assert stock["data"]["identity"]["ticker"] == "FRO"
    assert "research" not in stock["data"]
    assert brief["data"]["data_freshness"]
    assert path.read_bytes() == before


@pytest.mark.parametrize("question", ["", " ", "x" * 501])
def test_invalid_input_does_not_read_snapshot(question):
    with patch("jarvis.text_client.load_snapshot") as loader:
        with pytest.raises(JarvisCommandError):
            answer_question(question)
        loader.assert_not_called()


def test_streamlit_question_and_rejection(tmp_path, monkeypatch):
    path = tmp_path / "snapshot.json"
    path.write_text(json.dumps(fixture_snapshot()), encoding="utf-8")
    monkeypatch.setenv("INVESTMENT_OS_SNAPSHOT", str(path))
    app = AppTest.from_file("pages/1_Jarvis.py").run()
    assert not app.exception
    app.button[0].click().run()
    assert not app.exception
    assert "Porteføljesundhed" in str([item.value for item in app.text])
    assert app.warning  # The fixture is deliberately old; warnings stay visible.
    app.chat_input[0].set_value("Tænd lyset").run()
    assert not app.exception
    assert app.info
    assert "jarvis_answer" not in app.session_state
