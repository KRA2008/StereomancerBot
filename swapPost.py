import praw
import json

try:
    with open('creds.json','r') as file:
        creds = json.load(file)

    reddit = praw.Reddit(
        client_id=creds['RedditClientId'],
        client_secret=creds['RedditClientSecret'],
        password=creds['RedditPassword'],
        username=creds['RedditUsername'],
        user_agent="windows:com.kra2008.stereomancerbot:v2 (by /u/kra2008)"
    )
except OSError as e:
    print(f"OSError caught: {e}")
    print(f"OSError number (errno): {e.errno}")
    print(f"Operating system error code (winerror on Windows): {getattr(e, 'winerror', 'N/A')}")
    print(f"Error message: {e.strerror}")
except Exception as e:
    print(f"Error caught: {e}")
    print(f"Error message: {e.strerror}")