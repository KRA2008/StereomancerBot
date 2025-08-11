import praw
import json
import pprint
from difflib import SequenceMatcher
from PIL import Image
import requests
from io import BytesIO
import skia-python

with open('creds.json','r') as file:
    creds = json.load(file)

with open('CrossPosted.txt','r') as file:
    crossPosted = file.read()

reddit = praw.Reddit(
    client_id=creds['RedditClientId'],
    client_secret=creds['RedditClientSecret'],
    password=creds['RedditPassword'],
    username=creds['RedditUsername'],
    user_agent="windows:com.kra2008.stereomancerbot:v2 (by /u/kra2008)"
)

postsLimit = 15
originPosts = reddit.subreddit("crossview").new(limit=postsLimit)
destinationPostTitles = [post.title for post in reddit.subreddit("parallelview").new(limit=postsLimit)]

def duplicatesFilter(post):
    for title in destinationPostTitles:
        if SequenceMatcher(None, post.title, title).ratio() > 0.8:
            return True
    return False

eligiblePosts = [post for post in originPosts 
                 if post.is_video == False and                          #keep videos out for now
                 hasattr(post,'is_gallery') == False and                #keep galleries out for now
                 post.url.endswith('.jpeg') and
                 post.id not in crossPosted and
                 post.author.name not in creds['OptedOutUsers'] and
                 post.author.name != 'StereomancerBot' and
                 post.upvote_ratio > 0.5 and
                 duplicatesFilter(post) == False]

for post in eligiblePosts:
    print(post.title)
    imageResponse = requests.get(post.url)
    originalImage = Image.open(BytesIO(response.content))

#     print(post.id)
#     print(post.author)
    # pprint.pprint(vars(post))