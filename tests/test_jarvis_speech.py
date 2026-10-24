"""Speech safety and JavaScript controller tests, plus Streamlit integration."""
import json
import re
import shutil
import subprocess
from unittest.mock import patch

import pytest
from streamlit.testing.v1 import AppTest

from jarvis.speech import speech_html
from tests.test_jarvis_api import fixture_snapshot


def test_answer_is_inert_json_not_executable_markup():
    text = '</script><script>alert("x")</script>& dansk æøå'
    html = speech_html(text, "request-1", autoplay=True)
    assert html.count("<script>") == 1
    assert html.count("</script>") == 1
    config = re.search(r"const config = (.*);", html).group(1)
    assert json.loads(config)["text"] == text


HARNESS = r"""
const vm = require("node:vm"), assert = require("node:assert/strict");
const script = JSON.parse(require("node:fs").readFileSync(0,"utf8"));
function setup({enabled=true, voices=true, seen=null}={}) {
  const elements = {status:{},play:{},stop:{}}, events={}, timers=new Map();
  const spoken=[], stored=new Map([["jarvis-spoken-answer",seen]]);
  let cancellations=0, id=0;
  const synth={
    getVoices:()=>voices?[{lang:"da-DK",localService:true,name:"Danish"}]:[],
    speak:u=>spoken.push(u), cancel:()=>cancellations++,
    addEventListener:(e,f)=>events[e]=f,
    removeEventListener:(e,f)=>{if(events[e]===f) delete events[e];}
  };
  const context={document:{getElementById:id=>elements[id]},
    sessionStorage:{getItem:k=>stored.get(k),setItem:(k,v)=>stored.set(k,v)},
    setTimeout:f=>{timers.set(++id,f);return id;},clearTimeout:i=>timers.delete(i),
    window:{speechSynthesis:enabled?synth:null,
      SpeechSynthesisUtterance:function(t){this.text=t;},
      addEventListener:(e,f)=>events[e]=f}
  };
  context.SpeechSynthesisUtterance=context.window.SpeechSynthesisUtterance;
  vm.runInNewContext(script,context);
  return {elements,events,timers,spoken,get cancellations(){return cancellations;}};
}
let s=setup();
assert.equal(s.spoken.length,1);
assert.equal(s.spoken[0].lang,"da-DK");
assert.equal(s.spoken[0].voice.lang,"da-DK");
const old=s.spoken[0];
s.elements.stop.onclick();
old.onend();
assert.equal(s.spoken.length,1,"Stop must prevent remaining chunks");
s.elements.play.onclick();
assert.equal(s.spoken.length,2,"Replay is possible by explicit click");
s.spoken[1].onerror({error:"not-allowed"});
assert.match(s.elements.status.textContent,/kræver et klik/);
s=setup({voices:false});
assert.equal(s.spoken.length,0);
s.elements.stop.onclick();
assert.equal(s.timers.size,0);
assert.equal(s.events.voiceschanged,undefined);
s=setup({voices:false});
s.events.voiceschanged();
assert.equal(s.spoken.length,1);
s=setup({enabled:false});
assert.equal(s.elements.play.disabled,true);
assert.match(s.elements.status.textContent,/understøtter ikke/);
s=setup({seen:"answer-1"});
assert.equal(s.spoken.length,0,"Same request must not replay on remount");
s=setup();
let guard=0;
while(guard++<20 && s.spoken.at(-1).onend) {
  const last=s.spoken.at(-1);
  last.onend();
  if(s.spoken.at(-1)===last) break;
}
assert.equal(s.spoken.map(u=>u.text).join(""),"En dansk sætning. ".repeat(45));
assert.match(s.elements.status.textContent,/færdig/);
"""


def test_browser_speech_controller():
    node = shutil.which("node")
    if not node:
        pytest.skip("Node.js required for speech-controller execution")
    html = speech_html("En dansk sætning. " * 45, "answer-1", autoplay=True)
    script = re.search(r"<script>([\\s\\S]*)</script>", html).group(1)
    subprocess.run([node, "-e", HARNESS], input=json.dumps(script), text=True,
                   capture_output=True, check=True, timeout=15)


def test_speech_setting_does_not_repeat_existing_answer():
    with patch("jarvis.text_client.load_snapshot", return_value=fixture_snapshot()):
        app = AppTest.from_file("pages/1_Jarvis.py").run()
        app.button[0].click().run()
        assert not app.exception
        result_before = app.session_state["jarvis_answer"]
        app.toggle[0].set_value(False).run()
        assert not app.exception
        assert app.session_state["jarvis_answer"] == result_before
        assert app.toggle[0].value is False
