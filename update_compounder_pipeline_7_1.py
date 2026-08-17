from pathlib import Path


APP = Path("app.py")
text = APP.read_text(encoding="utf-8")

text = text.replace('page_title="Investment OS 7.0"', 'page_title="Investment OS 7.1"')
text = text.replace('st.title("📈 Investment OS 7.0")', 'st.title("📈 Investment OS 7.1")')
text = text.replace('APP_VERSION = "7.0.0"', 'APP_VERSION = "7.1.0"')

old_header = '''with tab_compounders:\n    st.subheader("Emerging Compounders")\n\n    if compounder_error:'''
new_header = '''with tab_compounders:\n    st.subheader("Emerging Compounders")\n    st.caption(\n        "7.1 kombinerer den mekaniske kvant-radar med mandags-agentens "\n        "intelligence-lag. Discovery Score er research-prioritering – ikke et købssignal."\n    )\n\n    if compounder_error:'''
if old_header in text:
    text = text.replace(old_header, new_header, 1)
elif new_header not in text:
    raise RuntimeError("Compounder header block not found")

old_metrics = '''        c1, c2, c3, c4 = st.columns(4)\n        c1.metric("Kandidater", compounder_summary["Candidate_Count"])\n        c2.metric("AI ≥ 80%", compounder_summary["High_Confidence_Count"])\n        c3.metric(\n            "Gns. konfidens",\n            (\n                f"{compounder_summary['Average_Confidence']:.0f}%"\n                if pd.notna(compounder_summary["Average_Confidence"]) else "N/A"\n            ),\n        )\n        c4.metric("Topkandidat", compounder_summary["Top_Candidate"] or "N/A")'''
new_metrics = '''        c1, c2, c3, c4, c5 = st.columns(5)\n        c1.metric("Kandidater", compounder_summary["Candidate_Count"])\n        c2.metric("Nye", compounder_summary.get("New_Candidate_Count", 0))\n        c3.metric("Confidence ≥ 80%", compounder_summary["High_Confidence_Count"])\n        c4.metric(\n            "Gns. confidence",\n            (\n                f"{compounder_summary['Average_Confidence']:.0f}%"\n                if pd.notna(compounder_summary["Average_Confidence"]) else "N/A"\n            ),\n        )\n        c5.metric("Topkandidat", compounder_summary["Top_Candidate"] or "N/A")\n\n        if compounder_summary.get("Agent_Generated_At"):\n            st.caption(\n                f"Mandags-agent sidst opdateret: {compounder_summary['Agent_Generated_At']}"\n            )'''
if old_metrics in text:
    text = text.replace(old_metrics, new_metrics, 1)
elif new_metrics not in text:
    raise RuntimeError("Compounder metrics block not found")

old_rename = '''            radar = radar.rename(columns={\n                "Name": "Selskab", "Composite_Score": "Composite",\n                "AI_Confidence": "AI Confidence",\n                "Revenue_CAGR_5Y": "Omsætning CAGR 5Y",\n                "EPS_CAGR_5Y": "EPS CAGR 5Y",\n                "Gross_Margin": "Bruttomargin", "Upside_Pct": "Upside",\n                "Risk_Reward": "Risk/Reward", "Risk": "Risiko",\n                "Reason": "Begrundelse",\n            })'''
new_rename = '''            radar = radar.rename(columns={\n                "Name": "Selskab",\n                "Discovery_Score": "Discovery Score",\n                "Research_Priority": "Research",\n                "Pipeline_Source": "Kilde",\n                "Composite_Score": "Kvant Score",\n                "Agent_Score": "Agent Score",\n                "Unified_Confidence": "Confidence",\n                "Is_New": "Ny",\n                "Agent_Score_Change": "Δ Agent",\n                "Revenue_CAGR_5Y": "Omsætning CAGR 5Y",\n                "EPS_CAGR_5Y": "EPS CAGR 5Y",\n                "Gross_Margin": "Bruttomargin", "Upside_Pct": "Upside",\n                "Risk_Reward": "Risk/Reward", "Risk": "Kvant risiko",\n                "Agent_Risk": "Agent risiko",\n                "Reason": "Kvant begrundelse",\n                "Agent_Thesis": "Agent tese",\n                "News_Classification": "Nyhedsklasse",\n            })\n            for score_col in [\n                "Discovery Score", "Kvant Score", "Agent Score", "Confidence", "Δ Agent"\n            ]:\n                if score_col in radar.columns:\n                    radar[score_col] = radar[score_col].apply(\n                        lambda value: score_text(value, 0) if pd.notna(value) else "N/A"\n                    )\n            if "Ny" in radar.columns:\n                radar["Ny"] = radar["Ny"].map({True: "🆕", False: ""}).fillna("")'''
if old_rename in text:
    text = text.replace(old_rename, new_rename, 1)
elif new_rename not in text:
    raise RuntimeError("Compounder rename block not found")

APP.write_text(text, encoding="utf-8")
print("Investment OS updated to 7.1.0 Compounder Pipeline")
