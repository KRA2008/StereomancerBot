import praw
import json
import pprint
from difflib import SequenceMatcher
from PIL import Image
import requests
from io import BytesIO


try:
    with open('creds.json','r') as file:
        creds = json.load(file)

    crossPostedListName = 'CrossPosted.txt'
    with open(crossPostedListName,'r') as file:
        crossPosted = file.read()

    reddit = praw.Reddit(
        client_id=creds['RedditClientId'],
        client_secret=creds['RedditClientSecret'],
        password=creds['RedditPassword'],
        username=creds['RedditUsername'],
        user_agent="windows:com.kra2008.stereomancerbot:v2 (by /u/kra2008)"
    )

    def swapAndCrossPost(originSubName,destinationSubName):
        postsSearchLimit = 100
        postsMakeLimit = 10
        originSubreddit = reddit.subreddit(originSubName)
        destinationSubreddit = reddit.subreddit(destinationSubName)
        originPosts = originSubreddit.new(limit=postsSearchLimit)
        destinationPostTitles = [post.title for post in destinationSubreddit.new(limit=postsSearchLimit)]


        def duplicatesFilter(post):
            for title in destinationPostTitles:
                if SequenceMatcher(None, post.title, title).ratio() > 0.8:
                    return True
            return False


        eligiblePosts = [post for post in originPosts 
                         if post.is_video == False and                          #keep videos out for now
                         (hasattr(post,'is_gallery') == True or
                         post.url.endswith('.jpeg') or
                         post.url.endswith('.png') or
                         post.url.endswith('.jpg')) and
                         post.id not in crossPosted and
                         post.author.name not in creds['OptedOutUsers'] and
                         post.author.name != 'StereomancerBot' and
                         post.upvote_ratio > 0.5 and
                         duplicatesFilter(post) == False]
        print(f'found {len(eligiblePosts)} eligible posts')

        eligiblePosts = eligiblePosts[:postsMakeLimit]
        print(f'converting {len(eligiblePosts)} posts')

        def convertImage(imageUrl,imagePath):
            imageResponse = requests.get(imageUrl)
            originalImage = Image.open(BytesIO(imageResponse.content))
            originalWidth = originalImage.width
            originalHeight = originalImage.height
    
            swappedImage = originalImage.copy()

            leftStart = (int(originalWidth/-2),0)
            rightStart = (int(originalWidth/2),0)
            swappedImage.paste(originalImage,leftStart)
            swappedImage.paste(originalImage,rightStart)

            if swappedImage.mode in ('RGBA','P'):
                swappedImage = swappedImage.convert('RGB')

            tempFileName=imagePath
            swappedImage.save(tempFileName)


        for originalPost in eligiblePosts:

            print(originalPost.title)

            if hasattr(originalPost,'is_gallery') == False:
                tempFileName='temp/temp.jpg'
                convertImage(originalPost.url,tempFileName)
                #TODO handle body text?
                swappedPost = destinationSubreddit.submit_image(image_path=tempFileName,title=originalPost.title + ' (converted from r/' + originSubName + ')',nsfw=originalPost.over_18)



            else:
                convertedImages = []

                for ii,item in enumerate(originalPost.gallery_data['items']):
                    tempFileName=f'temp/temp{ii}.jpg'
                    convertImage(f'https://i.redd.it/{item['media_id']}.jpg',tempFileName)
                    convertedImages.append({'image_path':tempFileName})

                #TODO handle body text?
                swappedPost = destinationSubreddit.submit_gallery(title=originalPost.title + ' (converted from r/' + originSubName + ')',images=convertedImages,nsfw=originalPost.over_18)

            swappedPost.reply("Original post: " + originalPost.permalink + " by [" + originalPost.author.name + "](https://reddit.com/user/" + originalPost.author.name + ")"+
                            "\r\n\r\n" +
                            "I'm a bot made by [KRA2008](https://reddit.com/user/KRA2008) to help the stereoscopic 3D community on Reddit :) " +
                            "I convert posts between cross and parallel viewing and repost them between the two subs. " +
                            "Please message [KRA2008](https://reddit.com/user/KRA2008) if you have comments or questions.")

            originalPost.reply("I'm a bot made by [KRA2008](https://reddit.com/user/KRA2008) and I've converted this post to r/" + destinationSubName + " and you can see that here: " + swappedPost.permalink)

            with open(crossPostedListName,'a') as file:
                file.write(originalPost.id+'\n')

    # swapAndCrossPost('crossview','parallelview')
    swapAndCrossPost('parallelview','crossview')
except OSError as e:
    print(f"OSError caught: {e}")
    print(f"OSError number (errno): {e.errno}")
    print(f"Operating system error code (winerror on Windows): {getattr(e, 'winerror', 'N/A')}")
    print(f"Error message: {e.strerror}")
except Error as e:
    print(f"Error caught: {e}")
    print(f"Error number (errno): {e.errno}")
    print(f"Error message: {e.strerror}")