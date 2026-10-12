# Emerging Compounder data updates

The Sunday workflow generates only `data/compounder_radar.xlsx`. It does not
generate or publish the separately researched `data/compounder_agent.json`.
Preparing or validating a new agent JSON outside GitHub does not update the app.
The app must run a checkout/deployment containing the merged data commit.

## Publish researched agent data through a PR

1. Obtain the complete researched JSON, including the real `generated_at` with
   timezone, methodology version, candidate scores and source URLs. Do not infer
   scores or dates from a screenshot or update report.
2. Create a branch from current `main`. Keep incoming JSON outside `data/` until
   publication; do not replace the live file directly.
3. Validate it without writes:

   ```sh
   python scripts/import_compounder_agent.py /path/to/incoming.json --check-only
   ```

4. Read the SHA256 of the current published file:

   ```sh
   python -c "import hashlib; from pathlib import Path; print(hashlib.sha256(Path('data/compounder_agent.json').read_bytes()).hexdigest())"
   ```

5. Publish on the branch using that hash:

   ```sh
   python scripts/import_compounder_agent.py /path/to/incoming.json --expected-sha256 CURRENT_SHA256
   ```

   Import rejects malformed candidates, duplicate normalized tickers, invalid
   scores, missing/invalid/future dates, stale updates, methodology changes and
   concurrent edits. An exclusive lock prevents simultaneous imports. Atomic
   replacement keeps the previously published file intact on validation/write
   failure. All submitted scores, research fields and bytes are preserved.
   If a process is killed and leaves a `.json.lock`, verify no import is running
   before removing that lock and retrying with a freshly read hash.

6. Run `python -m pytest -q`, commit the agent JSON, and open a PR. Include the
   import receipt's candidate count, generated date and SHA256 in the PR.
   The quality gate validates the committed JSON as well as running tests.
   If a connector refuses a write, report the refusal and obtain approval through
   its supported flow; a refused write is not a published update.
7. After approved merge and deployment, reload Streamlit. Confirm the agent
   date/count/hash and quant date in Emerging Compounders. The app rereads both
   files on each rerun; no cached agent payload is used.

## Display and scoring

The UI shows separate agent and quant source paths and timestamps, agent count,
methodology and content hash, with a warning when agent data is at least eight
days old. `Generated_UTC` is read from the quant file; no filesystem modification
time is presented as research freshness. Invalid agent data is reported and the
quant layer remains available without claiming that the agent file was loaded.

The candidate KPI is the union of quant and agent tickers, so it can exceed the
agent count. All candidates are displayed rather than only the first 20. The
60/40 score/confidence blend, ranking and Promotion Gate remain unchanged.

At investigation time, main contained 22 agent candidates generated
`2026-09-28T08:48:59+02:00`, plus 30 quant candidates generated
`2026-10-11T13:53:24+00:00`. The reportedly prepared JSON with 25 candidates was
not present in the repository or its fetched branches. Its actual research
payload is still required; this fix deliberately does not fabricate it.
