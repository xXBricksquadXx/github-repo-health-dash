import requests
import pandas as pd
from dash import Dash, html, dcc, Input, Output, State
import plotly.express as px


# For now we hard-code a public repo.
# We'll make this dynamic in later steps.
GITHUB_OWNER = "plotly"
GITHUB_REPO = "dash"


def fetch_commits(owner: str, repo: str, per_page: int = 100) -> pd.DataFrame:
    """
    Fetch the latest commits from the GitHub REST API and return a DataFrame.

    Columns:
      - sha
      - commit_date (datetime)
      - author_name
      - author_login
      - message
    """
    url = f"https://api.github.com/repos/{owner}/{repo}/commits"
    params = {"per_page": per_page}

    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()
    data = response.json()

    records = []
    for item in data:
        commit = item.get("commit", {}) or {}
        author_info = commit.get("author", {}) or {}
        gh_author = item.get("author") or {}

        records.append(
            {
                "sha": item.get("sha"),
                "commit_date": author_info.get("date"),
                "author_name": author_info.get("name"),
                "author_login": gh_author.get("login"),
                "message": commit.get("message"),
            }
        )

    df = pd.DataFrame(records)

    if df.empty:
        return df

    # Convert to datetime and sort
    df["commit_date"] = pd.to_datetime(df["commit_date"], errors="coerce")
    df = df.dropna(subset=["commit_date"]).sort_values("commit_date")

    return df


# --- Prepare data once at startup (static for now) ---

df_commits = fetch_commits(GITHUB_OWNER, GITHUB_REPO)

if not df_commits.empty:
    # Commits per week time series
    commits_per_week = (
        df_commits.set_index("commit_date")
        .resample("W")
        .size()
        .rename("commit_count")
        .reset_index()
    )
else:
    commits_per_week = pd.DataFrame(columns=["commit_date", "commit_count"])


# --- Build Dash app ---

app = Dash(__name__)

DEFAULT_OWNER = "pandas-dev"   # you can change these defaults anytime
DEFAULT_REPO = "pandas"

app.layout = html.Div(
    style={"maxWidth": "900px", "margin": "0 auto", "fontFamily": "system-ui"},
    children=[
        html.H1("GitHub Repo Activity", style={"textAlign": "center"}),

        html.Div(
            style={
                "display": "flex",
                "gap": "0.5rem",
                "justifyContent": "center",
                "marginTop": "1rem",
                "marginBottom": "1rem",
            },
            children=[
                dcc.Input(
                    id="owner-input",
                    type="text",
                    value=DEFAULT_OWNER,
                    placeholder="owner (e.g. pandas-dev)",
                    style={"width": "30%"},
                ),
                dcc.Input(
                    id="repo-input",
                    type="text",
                    value=DEFAULT_REPO,
                    placeholder="repo (e.g. pandas)",
                    style={"width": "30%"},
                ),
                html.Button(
                    "Load data",
                    id="load-button",
                    n_clicks=0,
                    style={"padding": "0.4rem 0.8rem"},
                ),
            ],
        ),

        html.Div(id="error-message", style={"color": "crimson", "textAlign": "center"}),

        html.Hr(),

        html.Div(
            children=[
                html.H2("Commits per week (last ~100 commits)"),
                dcc.Graph(id="commits-graph"),
            ]
        ),

        html.Div(
            style={"marginTop": "2rem"},
            children=[
                html.H2("Top contributors (by commit count)"),
                dcc.Graph(id="contributors-graph"),
            ],
        ),

        html.Div(
            style={"marginTop": "2rem"},
            children=[
                html.P(
                    "Data source: GitHub REST API /repos/{owner}/{repo}/commits",
                    style={
                        "fontSize": "0.9rem",
                        "color": "#555",
                        "marginTop": "0.5rem",
                        "textAlign": "center",
                    },
                ),
            ],
        ),
    ],
)

@app.callback(
    [
        Output("commits-graph", "figure"),
        Output("contributors-graph", "figure"),
        Output("error-message", "children"),
    ],
    Input("load-button", "n_clicks"),
    State("owner-input", "value"),
    State("repo-input", "value"),
    prevent_initial_call=True,
)
def update_dashboard(n_clicks, owner, repo):
    if not owner or not repo:
        empty_fig = px.scatter(title="No data")
        return empty_fig, empty_fig, "Please enter both owner and repo."

    try:
        df_commits = fetch_commits(owner.strip(), repo.strip())
    except requests.HTTPError as e:
        empty_fig = px.scatter(title="No data")
        status = e.response.status_code if e.response is not None else "unknown"
        msg = f"GitHub API error (status {status}). Check that the repository exists and is public."
        return empty_fig, empty_fig, msg
    except Exception as e:
        empty_fig = px.scatter(title="No data")
        return empty_fig, empty_fig, f"Unexpected error: {e}"

    if df_commits.empty:
        empty_fig = px.scatter(title="No commits returned for this repository.")
        return empty_fig, empty_fig, "No commit data returned (empty result)."

    # --- Commits per week ---
    commits_per_week = (
        df_commits.set_index("commit_date")
        .resample("W")
        .size()
        .rename("commit_count")
        .reset_index()
    )

    fig_commits = px.line(
        commits_per_week,
        x="commit_date",
        y="commit_count",
        markers=True,
        labels={"commit_date": "Week", "commit_count": "Number of commits"},
        title=f"Commit activity over time for {owner}/{repo}",
    )

    # --- Top contributors (by commit count) ---
    contributors = (
        df_commits["author_login"]
        .fillna("unknown")
        .value_counts()
        .head(10)
        .rename_axis("author_login")
        .reset_index(name="commit_count")
    )

    fig_contrib = px.bar(
        contributors,
        x="author_login",
        y="commit_count",
        title="Top contributors (by number of commits)",
        labels={"author_login": "Author", "commit_count": "Commits"},
    )

    return fig_commits, fig_contrib, ""

if __name__ == "__main__":
    # debug=True for hot reload as you edit.
    app.run(debug=True)
