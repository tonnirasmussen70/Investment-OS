"""Display provenance separately for each radar layer."""
from datetime import datetime, timezone
from modules.compounder_updates import generated_time


def render_radar_status(st, radar, now=None):
    if radar.agent_generated_at:
        st.caption(f"Agent senest opdateret: {radar.agent_generated_at} · {radar.agent_candidate_count} agentkandidater")
        st.caption(f"Agentkilde: {radar.agent_source_path} · Metode: {radar.methodology_version} · SHA256: {radar.agent_sha256}")
        age = (now or datetime.now(timezone.utc)) - generated_time(radar.agent_generated_at)
        if age.days >= 8:
            st.warning("Agentdata er over en uge gamle. En klargjort opdatering vises først, når den er valideret og publiceret i repository.")
    else:
        st.warning("Ingen gyldig agentopdatering er indlæst.")
    if radar.source_path:
        st.caption(f"Kvantkilde: {radar.source_path} · Kvant senest opdateret: {radar.quant_generated_at or 'Ukendt (ikke dokumenteret i filen)'}")
    st.caption(f"Viser alle {len(radar.data)} kandidater i det samlede univers (kvant + agent).")
