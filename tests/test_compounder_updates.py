from copy import deepcopy
from contextlib import nullcontext
import ast
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from modules.compounder_engine import load_compounder_radar, _merge_pipeline, top_candidates
from modules.compounder_updates import publish_agent, validate_agent_payload


def payload(count=25, date="2026-10-05T08:00:00+02:00"):
    # Synthetic integration fixture, never published as investment research.
    return {"generated_at": date, "methodology_version": "7.1", "candidates": [
        {"ticker": f"TEST{i}", "name": f"Fixture {i}", "agent_score": 80,
         "agent_confidence": 85, "sources": ["https://example.com/research"]}
        for i in range(count)]}


def write(path, content):
    path.write_text(json.dumps(content), encoding="utf-8")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_atomic_publication_and_reload(tmp_path):
    target = tmp_path / "compounder_agent.json"
    digest = write(target, payload(22, "2026-09-28T08:48:59+02:00"))
    source = tmp_path / "incoming.json"
    write(source, payload())
    before = load_compounder_radar(tmp_path)
    assert before.agent_candidate_count == 22
    report = publish_agent(source, target, digest)
    assert report["candidate_count"] == 25
    assert target.read_bytes() == source.read_bytes()
    radar = load_compounder_radar(tmp_path)
    assert len(top_candidates(radar, limit=len(radar.data))) == 25
    assert radar.agent_generated_at == payload()["generated_at"]
    assert radar.agent_sha256 == report["sha256"]
    assert radar.agent_source_path == target
    assert not target.with_suffix(".json.lock").exists()


@pytest.mark.parametrize("mutation", [
    lambda p: p.update(generated_at="invalid"),
    lambda p: p.update(generated_at="2099-01-01T00:00:00Z"),
    lambda p: p.update(generated_at="2026-10-05T08:00:00"),
    lambda p: p.update(candidates=[]),
    lambda p: p["candidates"].append(deepcopy(p["candidates"][0])),
    lambda p: p["candidates"][0].update(agent_score=101),
    lambda p: p["candidates"][0].update(agent_score=float("nan")),
    lambda p: p["candidates"][0].update(is_new="false"),
    lambda p: p["candidates"][0].update(sources="https://example.com"),
    lambda p: p["candidates"].append("bad"),
])
def test_reject_bad_payload(mutation):
    value = payload()
    mutation(value)
    with pytest.raises(ValueError):
        validate_agent_payload(value)


@pytest.mark.parametrize("case", ["stale", "conflict", "methodology", "replace_failure", "locked"])
def test_failed_update_preserves_published_file(tmp_path, case):
    target = tmp_path / "compounder_agent.json"
    digest = write(target, payload(22, "2026-09-28T08:48:59+02:00"))
    original = target.read_bytes()
    incoming = payload()
    if case == "stale":
        incoming["generated_at"] = "2026-09-28T08:48:59+02:00"
    if case == "methodology":
        incoming["methodology_version"] = "8.0"
    if case == "conflict":
        digest = "0" * 64
    source = tmp_path / "incoming.json"
    write(source, incoming)
    if case == "locked":
        target.with_suffix(".json.lock").touch()
    with patch("modules.compounder_updates.os.replace", side_effect=OSError("interrupted")) if case == "replace_failure" else nullcontext():
        with pytest.raises((ValueError, OSError)):
            publish_agent(source, target, digest)
    assert target.read_bytes() == original
    if case != "locked":
        assert not target.with_suffix(".json.lock").exists()


def test_invalid_agent_falls_back_without_claiming_it_was_loaded(tmp_path):
    pd.DataFrame([{"Name": "Quant", "Ticker": "TEST0", "Composite_Score": 90,
                   "AI_Confidence": 80, "Status": "Monitor"}]).to_csv(tmp_path / "compounder_radar.csv", index=False)
    (tmp_path / "compounder_agent.json").write_text('{"candidates": ["bad"]}')
    radar = load_compounder_radar(tmp_path)
    assert len(radar.data) == 1
    assert radar.agent_generated_at is None
    assert radar.agent_source_path is None
    assert any("kunne ikke indlæses" in note for note in radar.notes)


def test_scoring_weights_unchanged():
    quant = pd.DataFrame([{"Name": "Quant", "Ticker": "A", "Composite_Score": 90, "AI_Confidence": 80, "Status": "Monitor"}])
    agent = pd.DataFrame([{"Agent_Name": "Agent", "Ticker": "A", "Agent_Score": 80, "Agent_Confidence": 90}])
    combined = _merge_pipeline(quant, agent).iloc[0]
    assert combined["Discovery_Score"] == 86
    assert combined["Unified_Confidence"] == 84
    assert combined["Pipeline_Source"] == "Kvant + Agent"


def test_streamlit_status_and_refresh(tmp_path):
    target = tmp_path / "compounder_agent.json"
    digest = write(target, payload(22, "2026-09-28T08:48:59+02:00"))
    code = f'''import streamlit as st
from modules.compounder_engine import load_compounder_radar, top_candidates
from modules.compounder_view import render_radar_status
from datetime import datetime, timezone
r = load_compounder_radar({str(tmp_path)!r})
render_radar_status(st, r, now=datetime(2026, 10, 7, tzinfo=timezone.utc))
st.dataframe(top_candidates(r, limit=len(r.data)))
'''
    app = AppTest.from_string(code).run()
    assert not app.exception
    assert app.warning
    assert "22 agentkandidater" in app.caption[0].value
    incoming = tmp_path / "incoming.json"
    write(incoming, payload())
    publish_agent(incoming, target, digest)
    app.run()
    assert not app.exception
    assert not app.warning
    assert "25 agentkandidater" in app.caption[0].value
    assert payload()["generated_at"] in app.caption[0].value
    assert str(target) in app.caption[1].value
    assert len(app.dataframe[0].value) == 25


def test_repository_data_provenance():
    directory = Path(__file__).resolve().parents[1] / "data"
    published = json.loads((directory / "compounder_agent.json").read_bytes())
    radar = load_compounder_radar(directory)
    assert radar.agent_candidate_count == len(published["candidates"])
    assert radar.agent_generated_at == published["generated_at"]
    assert radar.agent_sha256 == hashlib.sha256((directory / "compounder_agent.json").read_bytes()).hexdigest()
    quant = pd.read_excel(directory / "compounder_radar.xlsx")
    assert radar.quant_generated_at == pd.to_datetime(quant["Generated_UTC"], utc=True).iloc[0].isoformat()
    assert len(radar.data) >= radar.agent_candidate_count


@pytest.mark.parametrize("legacy", [False, True])
def test_actual_compounder_tab_displays_top_ten_without_truncating_source(legacy):
    root = Path(__file__).resolve().parents[1]
    source = (root / "app.py").read_text(encoding="utf-8")
    functions = "\n".join(ast.get_source_segment(source, node) for node in ast.parse(source).body
                          if isinstance(node, ast.FunctionDef) and node.name in {"score_text", "no_scroll_height"})
    tab = source.split("with tab_compounders:", 1)[1].split("with tab_watchlist:", 1)[0]
    code = f'''import streamlit as st
import pandas as pd
from modules.compounder_engine import load_compounder_radar, radar_summary, top_candidates
from modules.compounder_view import render_radar_status
from modules.styling import table_style
from modules.formatting import format_score
from types import SimpleNamespace
from modules.etf_candidates import CANDIDATE_LIMIT
def render_etf_candidates(st):
    pass  # ETF rendering is tested separately without a live Yahoo dependency.
{functions}
compounder_radar = load_compounder_radar({str(root / "data")!r})
if {legacy!r}:
    # Same dataset with exactly the fields available before PR #9. Simulates
    # a running Streamlit process retaining the pre-deployment engine module.
    compounder_radar = SimpleNamespace(**{{key: value for key, value in vars(compounder_radar).items()
        if key not in {{'agent_candidate_count', 'agent_sha256', 'quant_generated_at'}}}})
compounder_summary = radar_summary(compounder_radar)
compounder_error = None
tab_compounders = st.container()
with tab_compounders:{tab}
'''
    app = AppTest.from_string(code, default_timeout=20).run()
    assert not app.exception
    radar = load_compounder_radar(root / "data")
    assert app.metric[0].value == str(min(10, len(radar.data)))
    assert len(app.dataframe[0].value) == min(10, len(radar.data))
    assert app.dataframe[0].value["Ticker"].tolist() == radar.data.head(10)["Ticker"].tolist()
    assert len(radar.data) > 10
    captions = "\n".join(item.value for item in app.caption)
    assert radar.agent_generated_at in captions
    if legacy:
        assert f"{radar.agent_candidate_count} agentkandidater" in captions
        assert "SHA256: Ikke tilgængelig" in captions
        assert "Ukendt (metadata ikke tilgængelige)" in captions
        assert any("ældre radarindlæsning" in item.value for item in app.warning)
    else:
        assert radar.quant_generated_at in captions
    assert str(radar.agent_source_path) in captions
