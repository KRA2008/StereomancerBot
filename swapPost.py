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

    def swapSidesAndUpload(post):
        if hasattr(originalPost,'is_gallery') == False:
        else:

    def checkForSwaps(subredditName):
        maxPostsSearch=100
        posts = reddit.subreddit(subredditName).new(limit=maxPostsSearch)
        posts = [post for post in originPosts 
                if post.is_video == False and                          #keep videos out for now
                (hasattr(post,'is_gallery') == True or
                post.url.endswith('.jpeg') or
                post.url.endswith('.png') or
                post.url.endswith('.jpg'))]

        for post in posts:
            for comment in post.comments.list():
                if comment.body == '!swap':
                    fixedPost = swapSidesAndUpload(post)

    # checkForSwaps('crossview')
    # checkForSwaps('parallelview')
    checkForSwaps('test')
except OSError as e:
    print(f"OSError caught: {e}")
    print(f"OSError number (errno): {e.errno}")
    print(f"Operating system error code (winerror on Windows): {getattr(e, 'winerror', 'N/A')}")
    print(f"Error message: {e.strerror}")
except Exception as e:
    print(f"Error caught: {e}")
    print(f"Error message: {e.strerror}")