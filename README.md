# GitHub Repo Health Dashboard (Dash + GitHub API)

A small analytics dashboard built with [Plotly Dash](https://dash.plotly.com/) that inspects the
recent commit history of any public GitHub repository.

It is designed as a **practical data-wrangling tutorial**:

1. Call the GitHub REST API.
2. Normalize JSON into a pandas DataFrame.
3. Aggregate to meaningful metrics.
4. Visualize activity and contributors in Dash.

---

## Features

- **Repo selector** – enter any public `owner/repo` and load the latest commits.
- **Commits per week** – line chart of activity over time (last ~100 commits).
- **Top contributors** – bar chart of authors ranked by commit count.
- **Health summary cards**:
  - Commits in sample
  - Unique authors
  - Commit date range covered
  - Top author share (approximate “bus factor” signal)

---

## How it works (data flow)

1. The app calls the GitHub REST API:

   ```text
   GET /repos/{owner}/{repo}/commits?per_page=100
   ```

2. The JSON response is normalized into a pandas DataFrame with columns like:

- `sha`
- `commit_date` (parsed to `datetime`)
- `author_name`
- `author_login`
- `message`

3. From there:

- Commits per week: `df.set_index("commit_date").resample("W").size()`
- Top contributors: `df["author_login"].value_counts()`

4. Dash renders:

- A line chart of commits/week.
- A bar chart of the top 10 contributors.
- Summary metrics in cards at the top of the page.
  > This keeps the focus on wrangling a real API into something interpretable.

---

### Running locally

Prerequisites:

- Python 3.9+ recommended
- Git

**Clone and set up**:

```bash
git clone https://github.com/<your-username>/github-repo-health-dash.git
cd github-repo-health-dash

python -m venv .venv
# Windows (PowerShell):
#   .venv\Scripts\Activate
# Linux/macOS:
#   source .venv/bin/activate

pip install --upgrade pip
pip install dash pandas requests python-dotenv
```

**Run the Dash app:**

```bash
python app.py
```

**Then open your browser at:**

```text
http://127.0.0.1:8050/
```

> Type a public `owner` and `repo` (for example `pandas-dev` / `pandas`) and click **Load** data.

---

### Interpreting the metrics

- **Commits in sample** – how many recent commits were fetched from the API.
- **Unique authors** – number of distinct commit authors; low numbers may indicate a bus factor risk.
- **Commit date range** – how far back the current sample reaches.
- **Top author share** – percentage of commits in this sample attributed to the top author.
