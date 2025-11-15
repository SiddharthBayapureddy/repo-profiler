from fastapi import FastAPI, HTTPException
import uvicorn
import re # Regex
import asyncio

# Importing from directory
import github_client
import profiler

from fastapi.middleware.cors import CORSMiddleware

# Basemodels
from models import Repo_Input, Repo_Output

# Summary generator
from summary import generate_summary


# Creating an Fastapi instance
app = FastAPI(title="RepoProfiler")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (GET, POST, OPTIONS, etc.)
    allow_headers=["*"],  # Allows all headers
)


def get_repo_name_from_url(url: str) -> str:
    # Pull 'owner/repo' from a github url
    match = re.search(r"github\.com/([\w\-]+/[\w\-]+)", url)
    if not match:
        raise ValueError("Wrong url. Expected Github Repo URL: 'https://github.com/owner/repo'.")
    return match.group(1)




@app.post("/analyze/", response_model=Repo_Output)
async def analyze_repo(repo_input: Repo_Input):
    
    try:
        repo_name = get_repo_name_from_url(str(repo_input.repo_url))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    print(f"Starting analysis for: {repo_name}")

    # Fetching all the data
    try:
        (
            repo_data,
            contrib_data,
            issues_data,
            commit_data,
            root_files
        ) = await asyncio.gather(
            github_client.fetch_repo_details(repo_name),
            github_client.fetch_contributors_list(repo_name),
            github_client.fetch_all_issues(repo_name),
            github_client.fetch_commit_activity(repo_name),
            github_client.fetch_repo_root_files(repo_name)
        )
    except Exception as e:
        print(f"Failed to fetch main data: {e}")
        raise HTTPException(status_code=404, detail=f"Repository not found or API error: {e}")

    # Fetching dependency files
    dep_files_to_check = ["requirements.txt", "package.json"]
    files_to_fetch = []
    
    for f in root_files:
        if f['name'] in dep_files_to_check:
            files_to_fetch.append(f)
    
    # Create tasks to fetch content
    file_content_tasks = [
        github_client.fetch_file_content(repo_name, f['path']) 
        for f in files_to_fetch
    ]
    fetched_contents = await asyncio.gather(*file_content_tasks)
    
    # Map file name -> its content
    file_contents = {
        f['name']: content 
        for f, content in zip(files_to_fetch, fetched_contents)
    }
    print(f"Found dependency files: {list(file_contents.keys())}")
    
    # Running our profiler
    print(f"Running profiler on {repo_name}...")
    
    activity = profiler.calculate_activity_trends(commit_data, issues_data)
    issues = profiler.analyze_issue_health(issues_data)
    contributors = profiler.format_contributors(contrib_data)
    score = profiler.calculate_health_score(repo_data, activity, issues)
    dependency_analysis = profiler.analyze_dependencies(file_contents)
    
    # Context for Gemini
    print("Gathering data for AI summary...")
    summary_context = {
        'repo_name': repo_data.get('full_name'),
        'health_score': score,
        'description': repo_data.get('description'),
        'stars': repo_data.get('stargazers_count'),
        'last_updated': repo_data.get('pushed_at'),
        'license': repo_data.get('license', {}).get('name') if repo_data.get('license') else "None",
        'activity': {
            'commits_per_week_avg': activity.commits_per_week_avg,
            'new_issues': activity.new_issues,
            'closed_issues': activity.closed_issues
        },
        'issues': {
            'total_open_issues': issues.open_issues,
            'stale_issues': issues.stale_issues,
            'bug_issues': issues.bug_issues
        },
        'top_contributors': contributors
    }
    
    # Preparing the summary
    ai_summary = await generate_summary(summary_context)
    print("Summary generated.")
    
    # Building the final report

    report = Repo_Output(
        repo_name=repo_data.get('full_name'),
        repo_url=repo_data.get('html_url'),
        description=repo_data.get('description'),
        stars=repo_data.get('stargazers_count'),
        forks=repo_data.get('forks_count'),
        liscense=repo_data.get('license', {}).get('name') if repo_data.get('license') else None,
        last_updated=repo_data.get('pushed_at'),
        activity=activity,
        top_contributor=contributors,
        issues=issues,
        health_score=score,
        dependencies=dependency_analysis,
        summary=ai_summary
    )
    
    print(f"Analysis for {repo_name} complete.")
    return report


#if __name__ == "__main__":
#   uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)