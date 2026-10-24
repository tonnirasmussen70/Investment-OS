"""Jarvis text interface in the existing IOS Streamlit application."""
import streamlit as st
import streamlit.components.v1 as components

from api.service import StockNotFoundError
from jarvis.adapter import JarvisCommandError
from jarvis.text_client import answer_question
from jarvis.speech import speech_html

st.set_page_config(page_title="Jarvis · IOS", page_icon="💬", layout="centered")
st.title("Jarvis")
st.caption("Spørg til dine IOS-data")
auto_speech = st.toggle("Læs nye svar op automatisk", value=True, key="jarvis_auto_speech")
speech_slot = st.empty()
st.write("Start med et af disse spørgsmål, eller skriv en tilsvarende kommando:")
examples = (
    "Hvordan er status på min portefølje?",
    "Vis porteføljens signaler",
    "Hvad er status på Investment OS?",
)
question = None
for example in examples:
    if st.button(example, use_container_width=True):
        question = example
st.caption("Enkelt værdipapir: skriv fx Analyser FRO med en ticker fra IOS.")
typed = st.chat_input("Spørg Jarvis", max_chars=500)
question = typed or question

if question:
    # Replace rather than accumulate answers, so old results are not shown as current.
    st.session_state.pop("jarvis_answer", None)
    st.session_state["jarvis_question"] = question
    try:
        st.session_state["jarvis_answer"] = answer_question(question)
    except (JarvisCommandError, StockNotFoundError):
        st.info("Spørgsmålet eller tickeren blev ikke genkendt. Brug et af eksemplerne ovenfor.")
    except RuntimeError:
        st.error("IOS-data kunne ikke læses. Åbn IOS-overblikket og opdatér data.")
    except Exception:
        st.error("Jarvis kunne ikke besvare spørgsmålet. Prøv igen senere.")

if result := st.session_state.get("jarvis_answer"):
    with st.chat_message("user"):
        st.text(st.session_state["jarvis_question"])
    with st.chat_message("assistant"):
        data = result.get("data") or {}
        freshness = data.get("data_freshness") or {}
        st.caption("IOS-data pr. " + str(freshness.get("as_of") or data.get("as_of") or "ukendt"))
        for item in data.get("warnings") or []:
            st.warning(str(item.get("message") or item.get("code") or "Dataadvarsel"))
        if freshness.get("status") != "fresh":
            st.warning("Data er gamle eller tidspunktet er ukendt. Svaret beskriver det gemte snapshot.")
        st.text(result["message"])
        with st.expander("Datagrundlag"):
            st.json(data)

# A stable slot replaces the preceding speech frame, including on rejected questions.
speech_result = st.session_state.get("jarvis_answer")
speech_data = (speech_result or {}).get("data") or {}
spoken_parts = [
    str(item.get("message") or item.get("code") or "Dataadvarsel")
    for item in speech_data.get("warnings") or []
]
if speech_result:
    spoken_parts.append(speech_result["message"])
with speech_slot:
    components.html(
        speech_html(
            "\n".join(spoken_parts),
            str((speech_result or {}).get("request_id") or ""),
            autoplay=bool(question and speech_result and auto_speech),
        ),
        height=100,
    )
