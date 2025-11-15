from google import genai
import asyncio

from dotenv import load_dotenv
import os

load_dotenv()

try:
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
except Exception as e:
    print(f"Unexpected Error. Message : {e}")

# Client instance
client = genai.Client()


async def generate_summary(data : dict) -> str:

    # Prompt
    prompt = f"""

    Your objective is to provide a high-level summary of a GitHub Repository.
    Analyze the following data

    Repo Name : {data.get('repo_name')}
    Health Score: {data.get('health_score')}
    Description: {data.get('description')}
    Stars : {data.get('stars')}
    Last Updated : {data.get('last_updated')}
    License: {data.get('license')}
    Commits per week (avg) : {data.get('activity' , {}).get('commits_per_week_avg')}
    New issues (last 30d): {data.get('activity', {}).get('new_issues')}
    Closed issues (last 30d): {data.get('activity', {}).get('closed_issues')}

    Total Open Issues: {data.get('issues', {}).get('total_open_issues')}
    Stale Issues (>90d): {data.get('issues', {}).get('stale_issues')}
    Bug-labeled Issues: {data.get('issues', {}).get('bug_issues')}
    
    Contributors Count: {len(data.get('top_contributors', []))}


    Provide a Summary that contains the following:
        1. Overall summary, desc of project
        2. Overall health and activity levels
        3. Any major issues/flags?
        4. Is it good overall? or bad? Rating on a scale from 1-10 and reasoning/justification


    Start the summary directly, without any preamble

    """

    try:
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: client.models.generate_content(
                model="gemini-2.5-flash",
                contents = prompt,
            )
        )
        return response.text
    
    except Exception as e:
        print(f"Error Summary : {e}")
        return "Failed to Generate AI Summary. Try again!"
    


# Testing sample summary on fake data

if __name__ == "__main__":

    mock_data = {
        'repo_name': 'psf/requests',
        'health_score': 85.0,
        'description': 'A simple, yet elegant HTTP library.',
        'stars': 49000,
        'last_updated': '2025-11-14T10:00:00Z',
        'license': 'Apache 2.0',
        'activity': {
            'commits_per_week_avg': 5.2,
            'new_issues_': 20,
            'closed_issues': 18
        },
        'issues': {
            'total_open_issues': 150,
            'stale_issues': 15,
            'bug_issues': 5
        },
        'top_contributors': [{}, {}, {}, {}, {}]
    }

    async def main_test():
        print("generating Summary...")
        summary = await generate_summary(mock_data)
        
        with open("summary.txt" , "w") as file:
            file.writelines(summary)

        print("Summary Generated! Check summary.txt")

    asyncio.run(main_test())