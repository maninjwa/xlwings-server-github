import asyncio
import logging
from itertools import repeat
from typing import List, Tuple
from urllib.parse import parse_qs, urlparse

import httpx
import matplotlib.pyplot as plt
import pandas as pd
import xlwings as xw
from fastapi import APIRouter, Body, Security, status
from fastapi.exceptions import HTTPException

from .. import settings
from ..core.auth import User, authenticate

# Require authentication for all endpoints for this router
router = APIRouter(
    dependencies=[Security(authenticate)],
    prefix="/github",
    tags=["GitHub"],
)

BASE_URL = "https://api.github.com"
PAGE_SIZE = 100


logger = logging.getLogger(__name__)


@router.post("/issues")
async def analyze_issues(
    data: dict = Body, current_user: User = Security(authenticate)
):
    logger.info(f"Running query for {current_user.email}")

    # Google Sheet objects
    with xw.Book(json=data) as book:
        dashboard_sheet = book.sheets["Dashboard"]
        issues_sheet = book.sheets["Open Issues"]
        charts_sheet = book.sheets["Charts"]
        repo_name = dashboard_sheet["B12"].value
        if not repo_name or "/" not in repo_name:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="Please provide a repo in the form 'owner/repo'.",
            )

        # Total and closed issues over time in monthly buckets
        issues = await get_issues(repo_name)
        issues_per_month = []
        for col_name in ["created_at", "closed_at"]:
            issues[col_name] = pd.to_datetime(issues[col_name])
            issues_per_month.append(issues.set_index(col_name)["id"].resample("M").count())
        issues_per_month = pd.concat(issues_per_month, axis=1)
        issues_per_month.columns = ["Total Issues", "Closed Issues"]
        cumulative_issues_per_month = issues_per_month.cumsum()
        cumulative_issues_per_month = cumulative_issues_per_month.fillna(method="ffill")
        issues_state_value_counts = issues["state"].value_counts()

        # Write results back to Google Sheets
        dashboard_sheet["G3"].value = issues_state_value_counts.get("open")
        dashboard_sheet["G7"].value = issues_state_value_counts.get("closed")

        charts_target_cell = charts_sheet["A1"]
        charts_target_cell.expand().clear_contents()
        charts_target_cell.value = cumulative_issues_per_month

        issues_target_cell = issues_sheet["A1"]
        issues_target_cell.expand().clear_contents()
        issues.columns = [name.replace("_", " ").capitalize() for name in issues.columns]
        issues_target_cell.options(index=False).value = issues.loc[
            issues["State"] == "open", :
        ].drop(columns=["Id", "State", "Closed at"])

        # Matplotlib plot
        plt.style.use("fivethirtyeight")
        ax = cumulative_issues_per_month.plot.area(
            figsize=(9, 6), stacked=False, color=["#4185f4", "#ea4435"]
        )
        fig = ax.get_figure()
        fig.suptitle("Total vs. Closed Issues", fontsize=14, fontweight="bold")
        dashboard_sheet.pictures.add(
            image=fig,
            name="time_series",
            anchor=dashboard_sheet["I2"],
            export_options={"bbox_inches": "tight", "dpi": 80},
            update=True,
        )

        return book.json()


async def fetch(url: str, client: httpx.AsyncClient) -> httpx.Response:
    return await client.get(
        url,
        headers={
            "Authorization": f"token {settings.github_access_token}",
            "Accept": "application/vnd.github.v3+json",
        },
    )


async def get_urls(repo: str) -> Tuple[List, httpx.Response]:
    url = (
        "{BASE_URL}/repos/{repo}/issues"
        "?per_page={PAGE_SIZE}&page={page}&state=all&filter=all"
    )
    urls = [url.format(BASE_URL=BASE_URL, PAGE_SIZE=PAGE_SIZE, repo=repo, page=1)]
    async with httpx.AsyncClient() as client:
        response = await fetch(urls[0], client)
    if response.status_code != 200:
        error_message = response.json().get("message")
        raise HTTPException(
            response.status_code,
            detail=f"Error contacting GitHub: {error_message}"
            if error_message
            else f"Error contacting GitHub: {response.status_code}",
        )
    if response.links.get("last"):
        parsed_last_url = urlparse(response.links["last"]["url"])
        num_pages = int(parse_qs(parsed_last_url.query)["page"][0])
        for page in range(2, num_pages + 1):
            urls.append(
                url.format(BASE_URL=BASE_URL, PAGE_SIZE=PAGE_SIZE, repo=repo, page=page)
            )
    return urls, response


async def get_issues(repo_name: str) -> pd.DataFrame:
    urls, first_page_response = await get_urls(repo_name)
    parts = [pd.DataFrame(data=first_page_response.json())]
    async with httpx.AsyncClient() as client:
        responses = await asyncio.gather(*map(fetch, urls[1:], repeat(client)))
    for ix, response in enumerate(responses):
        if response.status_code != 200:
            error_message = response.json().get("message")
            raise HTTPException(
                response.status_code,
                detail=f"Error contacting GitHub: {error_message}"
                if error_message
                else f"Error contacting GitHub: {response.status_code}",
            )
        parts.append(pd.DataFrame(data=response.json()))
    issues = pd.concat(parts)

    issues["issue_url"] = (
        '=HYPERLINK("'
        + issues["html_url"]
        + '", "'
        + issues["number"].astype(str)
        + '")'
    )

    # Filter out pull requests rows and unused columns
    issues = issues.loc[
        issues["pull_request"].isna(),
        ["id", "issue_url", "title", "state", "comments", "created_at", "closed_at"],
    ]
    return issues
