# Smart Money · SEC Form 4

The collector reads stock positions and Watchlist from the published IOS
portfolio snapshot and candidates from the published compounder agent feed.
It resolves US listings against the SEC exchange/ticker file. Multiple
listings for the same issuer share one CIK and one filing history. An SEC
match does not guarantee the issuer is subject to Form 4 reporting.

The workflow runs on weekday mornings UTC, including exchange holidays, and
supports manual runs. After merge, set the GitHub Actions repository
variable `SEC_USER_AGENT` to the project name and a monitored contact email
before the first run. The SEC does not require a data subscription.
A successful run publishes one atomic `latest.json` with a 90-calendar-day
filing window, accession-level history and the verified coverage date. Git
retains prior snapshots. SEC errors leave the last verified snapshot intact.
If the published file itself becomes invalid, restore it from a verified
commit before rerunning.

A purchase is a priced, non-derivative Form 4 acquisition with code P, which
includes open-market and private purchases. The filing date and transaction
date are separate. Joint filings retain the owners as a group. Form 4/A and
potentially affected originals remain in the snapshot for audit and are
excluded from purchase totals and clusters pending manual reconciliation.
Clusters use two or more distinct individual reporting CIKs with direct
purchases in 30 calendar days, excluding filings flagged under Rule 10b5-1.
