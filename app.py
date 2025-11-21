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

DEFAULT_OWNER = "pandas-dev"
DEFAULT_REPO = "pandas"

card_style = {
    "padding": "0.75rem 1rem",
    "border": "1px solid #ddd",
    "borderRadius": "0.5rem",
    "minWidth": "180px",
    "textAlign": "center",
    "boxShadow": "0 1px 2px rgba(0,0,0,0.05)",
}

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

        html.Div(
            id="metrics-row",
            style={
                "display": "flex",
                "flexWrap": "wrap",
                "gap": "1rem",
                "justifyContent": "center",
                "marginBottom": "1rem",
            },
            children=[
                html.Div(
                    style=card_style,
                    children=[
                        html.Div(
                            "Commits in sample",
                            style={"fontSize": "0.8rem", "color": "#555"},
                        ),
                        html.Div(
                            "—",
                            id="metric-total-commits",
                            style={"fontSize": "1.4rem", "fontWeight": "600"},
                        ),
                    ],
                ),
                html.Div(
                    style=card_style,
                    children=[
                        html.Div(
                            "Unique authors",
                            style={"fontSize": "0.8rem", "color": "#555"},
                        ),
                        html.Div(
                            "—",
                            id="metric-unique-authors",
                            style={"fontSize": "1.4rem", "fontWeight": "600"},
                        ),
                    ],
                ),
                html.Div(
                    style=card_style,
                    children=[
                        html.Div(
                            "Commit date range",
                            style={"fontSize": "0.8rem", "color": "#555"},
                        ),
                        html.Div(
                            "—",
                            id="metric-date-range",
                            style={"fontSize": "1.0rem", "fontWeight": "600"},
                        ),
                    ],
                ),
                html.Div(
                    style=card_style,
                    children=[
                        html.Div(
                            "Top author share",
                            style={"fontSize": "0.8rem", "color": "#555"},
                        ),
                        html.Div(
                            "—",
                            id="metric-top-share",
                            style={"fontSize": "1.0rem", "fontWeight": "600"},
                        ),
                    ],
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
        Output("metric-total-commits", "children"),
        Output("metric-unique-authors", "children"),
        Output("metric-date-range", "children"),
        Output("metric-top-share", "children"),
        Output("error-message", "children"),
    ],
    Input("load-button", "n_clicks"),
    State("owner-input", "value"),
    State("repo-input", "value"),
    prevent_initial_call=True,
)
def update_dashboard(n_clicks, owner, repo):
    placeholder = "—"
    empty_fig = px.scatter(title="No data")

    if not owner or not repo:
        return (
            empty_fig,
            empty_fig,
            placeholder,
            placeholder,
            placeholder,
            placeholder,
            "Please enter both owner and repo.",
        )

    try:
        df_commits = fetch_commits(owner.strip(), repo.strip())
    except requests.HTTPError as e:
        status = e.response.status_code if e.response is not None else "unknown"
        msg = f"GitHub API error (status {status}). Check that the repository exists and is public."
        return (
            empty_fig,
            empty_fig,
            placeholder,
            placeholder,
            placeholder,
            placeholder,
            msg,
        )
    except Exception as e:
        return (
            empty_fig,
            empty_fig,
            placeholder,
            placeholder,
            placeholder,
            placeholder,
            f"Unexpected error: {e}",
        )

    if df_commits.empty:
        return (
            empty_fig,
            empty_fig,
            placeholder,
            placeholder,
            placeholder,
            placeholder,
            "No commit data returned (empty result).",
        )

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

    # --- Summary metrics ---
    total_commits = int(df_commits.shape[0])

    unique_authors = int(
        df_commits["author_login"].fillna("unknown").nunique()
    )

    start_date = df_commits["commit_date"].min().date()
    end_date = df_commits["commit_date"].max().date()
    date_range_str = f"{start_date} → {end_date}"

    counts = df_commits["author_login"].fillna("unknown").value_counts()
    if not counts.empty:
        top_author = counts.index[0]
        top_share = (counts.iloc[0] / total_commits) * 100
        top_share_str = f"{top_author}: {top_share:.1f}% of commits"
    else:
        top_share_str = placeholder

    return (
        fig_commits,
        fig_contrib,
        str(total_commits),
        str(unique_authors),
        date_range_str,
        top_share_str,
        "",
    )


if __name__ == "__main__":
    # debug=True for hot reload as you edit.
    app.run(debug=True)
