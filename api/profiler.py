# File: profiler.py

import json
import re
from datetime import datetime, timedelta
from typing import List, Dict, Any

# Import the exact models you defined in your models.py
from api.models import (
    Dependency, 
    DependencyAnalysis, 
    ActivityTrends, 
    IssueHealth, 
    Contributor
)

# --- 1. Dependency Analysis ---
# These functions parse dependency files.

def parse_requirements_txt(file_content: str) -> List[Dependency]:
    """Parses text from a requirements.txt file."""
    dependencies = []
    lines = file_content.split('\n')
    for line in lines:
        line = line.strip()
        # Skip empty lines or comments
        if not line or line.startswith('#'):
            continue
        
        # This regex handles 'package==version', 'package>=version', or just 'package'
        match = re.match(r'^([\w\-]+)(?:[=~>]{1,2}([\w\.]+))?', line)
        if match:
            name, version = match.groups()
            dependencies.append(Dependency(
                name=name, 
                version=version if version else "latest"
            ))
    return dependencies

def parse_package_json(file_content: str) -> List[Dependency]:
    """Parses text from a package.json file."""
    dependencies = []
    try:
        data = json.loads(file_content)
        # Combine regular dependencies and dev dependencies
        deps = data.get('dependencies', {})
        dev_deps = data.get('devDependencies', {})
        all_deps = {**deps, **dev_deps}
        
        for name, version in all_deps.items():
            dependencies.append(Dependency(name=name, version=version))
            
    except json.JSONDecodeError:
        pass  # Failed to parse, return empty list
    return dependencies

def analyze_dependencies(file_contents: Dict[str, str]) -> List[DependencyAnalysis]:
    """
    Orchestrates the parsing of different dependency files.
    'file_contents' is a dict mapping { "file_name.txt": "file_content_string" }
    """
    dependency_reports = []

    # Check for requirements.txt
    if "requirements.txt" in file_contents:
        content = file_contents["requirements.txt"]
        deps = parse_requirements_txt(content)
        if deps:
            dependency_reports.append(DependencyAnalysis(
                file="requirements.txt",
                dependencies=deps
            ))
            
    # Check for package.json
    if "package.json" in file_contents:
        content = file_contents["package.json"]
        deps = parse_package_json(content)
        if deps:
            dependency_reports.append(DependencyAnalysis(
                file="package.json",
                dependencies=deps
            ))

    # You would add more parsers here (pom.xml, Gemfile, etc.)
    
    return dependency_reports

# --- 2. Activity & Trend Analysis ---
# Calculates metrics for your 'ActivityTrends' model

def calculate_activity_trends(
    commit_activity: List[Dict[str, Any]],
    issues_list: List[Dict[str, Any]]
) -> ActivityTrends:
    """
    Calculates activity trends from commit and issue data.
    'commit_activity' is the 52-week summary from the API.
    'issues_list' is the list of all issues.
    """
    # Calculate commit trend
    total_commits = 0
    if commit_activity:
        for week in commit_activity:
            total_commits += week['total']
        avg_commits = total_commits / 52
    else:
        avg_commits = 0

    # Calculate issue trend (matches your model names)
    new_issues_count = 0
    closed_issues_count = 0
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)

    for issue in issues_list:
        created_at = datetime.fromisoformat(issue['created_at'].replace('Z', ''))
        if created_at > thirty_days_ago:
            new_issues_count += 1
        
        if issue['closed_at']:
            closed_at = datetime.fromisoformat(issue['closed_at'].replace('Z', ''))
            if closed_at > thirty_days_ago:
                closed_issues_count += 1

    return ActivityTrends(
        commits_per_week_avg=round(avg_commits, 2),
        new_issues=new_issues_count,
        closed_issues=closed_issues_count
    )

# --- 3. Issue Health Analysis ---
# Calculates metrics for your 'IssueHealth' model

def analyze_issue_health(issues_list: List[Dict[str, Any]]) -> IssueHealth:
    """Analyzes a list of issues for stale and bug reports."""
    total_open_issues = 0
    stale_issues_count = 0
    bug_issues_count = 0
    ninety_days_ago = datetime.utcnow() - timedelta(days=90)

    for issue in issues_list:
        if issue['state'] == 'open':
            total_open_issues += 1
            
            # Check for stale
            updated_at = datetime.fromisoformat(issue['updated_at'].replace('Z', ''))
            if updated_at < ninety_days_ago:
                stale_issues_count += 1
            
            # Check for 'bug' label
            for label in issue['labels']:
                if 'bug' in label['name'].lower():
                    bug_issues_count += 1
                    break # Stop checking labels for this issue

    return IssueHealth(
        open_issues=total_open_issues,
        stale_issues=stale_issues_count,
        bug_issues=bug_issues_count
    )

# --- 4. Contributor Analysis ---
# Formats data for your 'Contributor' model

def format_contributors(contrib_data: List[Dict[str, Any]]) -> List[Contributor]:
    """Converts raw contributor data into our Pydantic model."""
    contributors = []
    # Get top 5 contributors
    for contrib in contrib_data[:5]:
        contributors.append(Contributor(
            username=contrib['login'],
            commits=contrib['contributions']
        ))
    return contributors

# --- 5. Overall Scoring ---
# Calculates the 'health_score' for the 'Repo_Output' model

def calculate_health_score(
    repo_data: Dict[str, Any],
    activity: ActivityTrends,
    issues: IssueHealth
) -> float:
    """Calculates a single 0-100 health score."""
    score = 100.0

    try:
        # 'pushed_at' is the field from GitHub's API
        last_push = datetime.fromisoformat(repo_data['pushed_at'].replace('Z', ''))
        if last_push < (datetime.utcnow() - timedelta(days=90)):
            score -= 10 # 10 points off if no pushes in 3 months
    except Exception:
        score -= 10 # Penalize if 'pushed_at' is missing

    # Commit activity
    if activity.commits_per_week_avg < 1:
        score -= 20
    elif activity.commits_per_week_avg < 5:
        score -= 10

    # Issue health
    if issues.open_issues > 0:
        stale_ratio = issues.stale_issues / issues.open_issues
        score -= (stale_ratio * 20) # Up to 20 points off for stale
        
        bug_ratio = issues.bug_issues / issues.open_issues
        score -= (bug_ratio * 20) # Up to 20 points off for bugs
        
    # Popularity
    if repo_data.get('stargazers_count', 0) < 100:
        score -= 10
    
    # Has license?
    if not repo_data.get('license'):
        score -= 10
        
    # Has description?
    if not repo_data.get('description'):
        score -= 10

    return max(0.0, round(score, 2))