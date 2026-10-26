"""Browser speech controller; portfolio text is serialized as inert JSON, never HTML."""
from __future__ import annotations

import json


def speech_html(text: str, answer_id: str, *, autoplay: bool) -> str:
    config = json.dumps(
        {"text": text, "id": answer_id, "autoplay": bool(autoplay)},
        ensure_ascii=True,
    ).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    return _TEMPLATE.replace("__CONFIG__", config)


_TEMPLATE = r"""<!doctype html>
<html lang="da"><meta charset="utf-8">
<style>
body{font:14px system-ui;color:#aaa;margin:0}
button,select{font:inherit;padding:7px 12px;margin:0 8px 8px 0}
button{cursor:pointer}
</style>
<label for="voice">Dansk stemme</label>
<select id="voice" aria-label="Dansk stemme"></select>
<br>
<button id="play" type="button">Læs svaret op</button>
<button id="stop" type="button">Stop</button>
<div id="status" role="status" aria-live="polite"></div>
<script>
(() => {
  const config = __CONFIG__;
  const status = document.getElementById("status");
  const play = document.getElementById("play");
  const stop = document.getElementById("stop");
  const selector = document.getElementById("voice");
  const synth = window.speechSynthesis;
  let generation = 0, timer, utterance, readyHandler;
  const say = message => { status.textContent = message; };
  if (!synth || !window.SpeechSynthesisUtterance) {
    play.disabled = stop.disabled = selector.disabled = true;
    say("Browseren understøtter ikke oplæsning. Tekstsvaret kan stadig læses.");
    return;
  }
  const storageKey = "jarvis-preferred-voice";
  function savedVoice() {
    try { return localStorage.getItem(storageKey) || ""; } catch (_) { return ""; }
  }
  function refreshVoices() {
    const voices = synth.getVoices().filter(v => /^da(-|$)/i.test(v.lang));
    const selected = savedVoice();
    selector.replaceChildren();
    const automatic = document.createElement("option");
    automatic.value = "";
    automatic.textContent = "Automatisk (foretrækker lokal)";
    selector.appendChild(automatic);
    for (const voice of voices) {
      const option = document.createElement("option");
      option.value = voice.voiceURI || voice.name;
      option.textContent = voice.name + (voice.localService ? " (lokal)" : " (online)");
      selector.appendChild(option);
    }
    selector.value = voices.some(v => (v.voiceURI || v.name) === selected) ? selected : "";
    selector.disabled = !voices.length;
  }
  selector.onchange = () => {
    try { localStorage.setItem(storageKey, selector.value); } catch (_) { /* Storage may be blocked. */ }
  };
  refreshVoices();
  synth.addEventListener("voiceschanged", refreshVoices);
  function cancel() {
    generation++;
    clearTimeout(timer);
    if (readyHandler) synth.removeEventListener("voiceschanged", readyHandler);
    readyHandler = null;
    synth.cancel();
    utterance = null;
  }
  function speak() {
    cancel();
    if (!config.text) return;
    const current = generation;
    const voices = synth.getVoices();
    const danish = voices.filter(v => /^da(-|$)/i.test(v.lang));
    const voice = danish.find(v => (v.voiceURI || v.name) === selector.value)
      || danish.find(v => v.localService) || danish[0];
    const chunks = config.text.match(/[\s\S]{1,220}(?:\s|$)|[\s\S]{1,220}/g) || [];
    let index = 0;
    function next() {
      if (generation !== current) return;
      if (index >= chunks.length) {
        say("Oplæsning færdig.");
        return;
      }
      utterance = new SpeechSynthesisUtterance(chunks[index++]);
      utterance.lang = "da-DK";
      if (voice) utterance.voice = voice;
      utterance.rate = 1;
      utterance.onend = next;
      utterance.onerror = event => {
        if (generation !== current) return;
        cancel();
        say(event.error === "not-allowed"
          ? "Browseren kræver et klik. Tryk Læs svaret op."
          : "Oplæsning kunne ikke starte. Tryk Læs svaret op for at prøve igen.");
      };
      say(voice ? "Læser svaret op…" : "Læser op med browserens stemme. Dansk stemme er ikke fundet.");
      // Keep a strong reference to the active utterance until completion.
      synth.speak(utterance);
    }
    next();
  }
  play.onclick = speak;
  stop.onclick = () => { cancel(); say("Oplæsning stoppet."); };
  window.addEventListener("pagehide", () => { cancel(); synth.removeEventListener("voiceschanged", refreshVoices); });
  // Cancel the preceding answer when this component is replaced.
  cancel();
  if (!config.text) {
    play.disabled = stop.disabled = true;
    return;
  }
  say("Klar til oplæsning. Hvis automatisk start blokeres, tryk Læs svaret op.");
  if (config.autoplay) {
    // Store only the request ID, never portfolio text. Rerenders must not replay it.
    let seen = false;
    try {
      seen = sessionStorage.getItem("jarvis-spoken-answer") === config.id;
      sessionStorage.setItem("jarvis-spoken-answer", config.id);
    } catch (_) { /* Storage can be unavailable in restricted browsers. */ }
    if (!seen) {
      if (synth.getVoices().length) speak();
      else {
        const ready = () => {
          clearTimeout(timer);
          synth.removeEventListener("voiceschanged", ready);
          speak();
        };
        readyHandler = ready;
        synth.addEventListener("voiceschanged", ready, {once:true});
        timer = setTimeout(ready, 800);

      }
    }
  }
})();
</script></html>"""
