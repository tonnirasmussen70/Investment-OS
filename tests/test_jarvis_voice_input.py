"""Exercise microphone controller without recording or network access."""
import json
from pathlib import Path
import re
import shutil
import subprocess
from unittest.mock import patch

import pytest


HARNESS = r"""
const vm = require('node:vm'), assert = require('node:assert/strict');
const script = JSON.parse(require('node:fs').readFileSync(0, 'utf8'));
let instance, starts=0, sent=[], elements={mic:{},status:{}};
function Recognition() { instance=this; this.start=()=>{starts++; this.onstart()}; this.stop=()=>this.onend(); this.abort=()=>{}; }
const ctx={window:{SpeechRecognition:Recognition,parent:{postMessage:m=>sent.push(m)},addEventListener:()=>{}},
 document:{getElementById:id=>elements[id]}, Date, Math};
vm.runInNewContext(script,ctx);
assert.equal(starts,0,'microphone must require a click');
elements.mic.onclick();
assert.equal(starts,1);
assert.equal(instance.lang,'da-DK');
instance.onresult({results:[[{transcript:'  Vis porteføljens signaler  '}]]});
const result=sent.find(m=>m.type==='streamlit:setComponentValue');
assert.equal(result.value.text,'Vis porteføljens signaler');
assert.ok(result.value.id);
instance.onerror({error:'not-allowed'});
assert.match(elements.status.textContent,/blokeret/);
instance.onend();
assert.match(elements.mic.textContent,/stemmen/);
"""


def test_microphone_requires_click_and_submits_danish_text():
    node = shutil.which("node")
    if not node:
        pytest.skip("Node.js required for browser-controller test")
    html = Path("jarvis/voice_input/index.html").read_text(encoding="utf-8")
    script = re.search(r"<script>([\s\S]*)</script>", html).group(1)
    subprocess.run([node, "-e", HARNESS], input=json.dumps(script), text=True,
                   capture_output=True, check=True, timeout=15)


def test_voice_question_requires_confirmation_and_can_be_corrected():
    from streamlit.testing.v1 import AppTest
    from tests.test_jarvis_api import fixture_snapshot

    event = {"id": "voice-1", "text": "misforstået tekst"}
    with patch("jarvis.voice_input.voice_input", return_value=event), \
         patch("jarvis.text_client.load_snapshot", return_value=fixture_snapshot()):
        app = AppTest.from_file("pages/1_Jarvis.py").run()
        assert not app.exception
        assert app.text_input[0].value == event["text"]
        assert "jarvis_answer" not in app.session_state
        app.text_input[0].set_value("Vis porteføljens signaler")
        app.button[-1].click().run()
        assert not app.exception
        assert app.session_state["jarvis_question"] == "Vis porteføljens signaler"
        original = app.session_state["jarvis_answer"]
        app.run()
        assert not app.exception
        assert app.session_state["jarvis_answer"] == original
