from pydantic import BaseModel , HttpUrl  # Used for Datavalidation form user
from typing import List, Optional


# Input Model
# This defines the input expected from the user. Expecting a valid github repourl
class Repo_Input(BaseModel):
    repo_url = HttpUrl  # Checking if it's a valid url

# Contributors Model
class Contributor(BaseModel):
    username: str
    commits: int

#-------------------------------------------------------------------
# Dependency Model
class Dependency(BaseModel):
    name: str
    version : str

# Dependency Analysis Model
class DependencyAnalysis(BaseModel):
    file : str
    dependencies: List[Dependency]
#----------------------------------------------------------------------

# Activity Trends
class ActivityTrends(BaseModel):
    commits_per_week_avg: float
    new_issues: int
    closed_issues: int

class IssueHealth(BaseModel):
    open_issues: int
    stale_issues: int  # Issues not resolved in last 90days
    bug_issues: int 

#----------------------------------------------------------------------

# Output model
class Repo_Output(BaseModel):
    
    # Defines the output that is sent back to the user. (Essentially the full report/summary)

    repo_name : str
    repo_url : HttpUrl
    description: Optional[str] = None

    # Health Score Metrics
    stars: int
    forks: int
    liscense : Optional[str] = None
    last_updated: str

    # Activity
    activity : Optional[ActivityTrends] = None
    top_contributor : List[Contributor] = []

    # Issues
    issues : Optional[IssueHealth] = None
    health_score : float

    # Summary 
    summary: str