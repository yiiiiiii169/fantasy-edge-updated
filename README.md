# Fantasy Edge — Browser Website Edition

A private ESPN Fantasy Basketball assistant tuned for **12-team head-to-head points** leagues. Trade ideas, waiver add/drop comparisons, weekly player-game schedules, injury flags, recent-form trends, and side-by-side matchup estimates. **Read only**: does not execute moves.

**No Python installation required.** Follow the browser-only instructions below to publish your personal website.

## Publish your own private website (no coding)

1. Sign in to https://github.com and create a repository named `fantasy-edge`. Choose **Private**. Do **not** paste or upload ESPN cookies to GitHub.
2. In the repository, click **Add file → Upload files**. Extract the downloaded ZIP from ChatGPT and upload these files from inside the extracted folder: `app.py`, `engine.py`, `espn_client.py`, `requirements.txt`, `README.md`. The files must appear at the top level of the repository (not hidden inside a second folder). Click **Commit changes**.
3. Go to https://share.streamlit.io/ and sign in. Connect GitHub when prompted. Select **Create app**, choose repository `fantasy-edge`, branch `main` (or whatever branch GitHub shows), and main file `app.py`. Deploy.
4. In your Streamlit app settings, set **app visibility to Private/restricted access**. Confirm you are the only viewer. A *private GitHub repository alone does not guarantee the deployed app is private*. Do not enter ESPN cookies until the web app itself is private.
5. Open your new `*.streamlit.app` website in your browser. It runs online; you do not need Python or a command line. Streamlit Community Cloud availability, UI and allowances may change.

Official help: https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy and https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app/app-settings

## Connect your ESPN private fantasy league

1. Log in to https://fantasy.espn.com/basketball/ and open your specific league. The `leagueId` parameter in your league URL is the numeric **League ID**.
2. Set the ESPN **season year** (the 2026–27 season is **2027**).
3. While logged in to ESPN in Chrome, open Developer Tools (Mac: `Option+Command+I`; Windows: `F12`) and locate **Application → Storage → Cookies**. Find cookies named `espn_s2` and `SWID` under ESPN's domain.
4. **Only on your private deployed app**, enter those two cookie values into the password fields in the sidebar, then click **Connect / refresh league**. They may expire. Do not email them, paste them into ChatGPT, commit them to GitHub, use a shared public app, or capture them in a screenshot. Because a deployed Streamlit app runs on a hosted server, the cookie values are sent to Streamlit's hosting environment when entered; hosting the app is not the same as keeping the cookies solely on your laptop.
5. Click **Refresh NBA schedule**. Select your fantasy team and your weekly opponent on the matchup tab. Refresh whenever you want new information. Nothing is auto-synced in the background.

## How to use it

- **Roster & form:** Check last-7 and season fantasy points per game.
- **H2H matchup:** Compare projected whole-roster opportunities with a selected opponent (not an exact starting-lineup score or win probability).
- **Waiver radar:** Find add/drop combinations improving this week's opportunities. Check roster/transaction rules before acting.
- **Trade lab:** Compare 1-for-1 and 2-for-1 packages; remember to value the open roster slot and long-term upside.
- **Schedule edge:** See days where extra games might make a streaming pickup more useful.
- **Risk & strategy:** Monitor injury flags and hot/cold recent production.

## Important limitations

- Uses an **unofficial ESPN fantasy API** through `espn-api`, which ESPN may change or restrict. No official ESPN authorization flow is provided.
- League must be accessible to your ESPN account. Not all ESPN splits and injury statuses are always available; schedule data may have gaps.
- Stats are only as good as ESPN responses; the model defaults to weighted last-7 / last-15 / season averages, with simple heuristic injury discounts.
- Uses ESPN's per-game applied fantasy scores where provided, to reflect your league's custom points scoring. It does not yet reconcile custom matchup scoring periods, active positions, benches, IL slots, position eligibility, games caps, or add limits.
- Twelve-team league setting is a recommendation context, not a promise that league settings or matchups are automatically inferred. Weekly opponent is selected manually.
- ESPN credentials are not stored to file by this project; they still travel to the hosting provider's server when submitted. Use private app access. Do not save secrets in repository files.
- Not affiliated with or endorsed by ESPN or the NBA.

## Deployment checklist

- [ ] GitHub repository is private
- [ ] Streamlit **app** access is private and restricted to me
- [ ] Uploaded five files, **not** the ZIP file itself
- [ ] Selected `app.py` as the main file
- [ ] Credentials were only entered into my own deployed, private app
- [ ] League year, league ID and team name verified
- [ ] NBA schedule refreshed
