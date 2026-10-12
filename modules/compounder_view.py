"""Display provenance separately for each radar layer."""
from datetime import datetime, timezone
from modules.compounder_updates import generated_time


def render_radar_status(st, radar, now=None):
    # Streamlit can retain an imported engine/old radar class during a live
    # deployment. Read optional metadata defensively; never reread a different
    # source file and attribute its metadata to this already-loaded dataset.
    agent_date = getattr(radar, "agent_generated_at", None)
    agent_count = getattr(radar, "agent_candidate_count", None)
    if agent_count is None and "Agent_Score" in radar.data.columns:
        agent_count = int(radar.data["Agent_Score"].notna().sum())
    if agent_date:
        st.caption(f"Agent senest opdateret: {agent_date} · {agent_count if agent_count is not None else 'Ukendt antal'} agentkandidater")
        st.caption(f"Agentkilde: {getattr(radar, 'agent_source_path', None) or 'Ukendt'} · Metode: {getattr(radar, 'methodology_version', None) or 'Ukendt'} · SHA256: {getattr(radar, 'agent_sha256', None) or 'Ikke tilgængelig'}")
        try:
            age = (now or datetime.now(timezone.utc)) - generated_time(agent_date)
        except ValueError:
            st.warning("Agentens opdateringsdato kunne ikke valideres.")
        else:
            if age.days >= 8:
                st.warning("Agentdata er over en uge gamle. En klargjort opdatering vises først, når den er valideret og publiceret i repository.")
    else:
        st.warning("Ingen gyldig agentopdatering er indlæst.")
    if radar.source_path:
        st.caption(f"Kvantkilde: {radar.source_path} · Kvant senest opdateret: {getattr(radar, 'quant_generated_at', None) or 'Ukendt (metadata ikke tilgængelige)'}")
    if not hasattr(radar, "agent_candidate_count"):
        st.warning("Appen bruger en ældre radarindlæsning. Genstart appen for at indlæse alle opdateringsmetadata.")
    st.caption(f"Viser alle {len(radar.data)} kandidater i det samlede univers (kvant + agent).")
