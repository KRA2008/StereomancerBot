import asyncpraw
import json
import pprint
from difflib import SequenceMatcher
import stereoConvert
import os
import asyncio
from aiohttp import ClientSession

# testing = True
testing = False

crossPostedListName = 'CrossPosted.txt'
credsFileName = 'creds.json'
userAgent = 'windows:com.kra2008.stereomancerbot:v2 (by /u/kra2008)'


async def processGalleryItem(ii,jj,originalPost,item,destinationSub,session,convertedImages):
    try:
        f,extension = os.path.splitext(originalPost.url)
        tempFileName=f'temp/{destinationSub.display_name}temp{ii}_{jj}{extension}'
        await stereoConvert.convertImage(f'https://i.redd.it/{item['media_id']}.jpg',tempFileName,userAgent,session)
        if os.path.isfile(tempFileName) == False:
            return
        convertedImages.append({'image_path':tempFileName})
    except Exception as ex:
        print('processGalleryItems ex: ' + ex)
        raise

async def processPost(ii,originalPost,originSub,destinationSub,session):
    try:
        print(f'{originalPost.title}, {originalPost.id}')
        # pprint.pprint(vars(originalPost))

        if hasattr(originalPost,'is_gallery') == False:
            f,extension = os.path.splitext(originalPost.url)
            tempFileName=f'temp/{destinationSub.display_name}temp{ii}{extension}'
            await stereoConvert.convertImage(originalPost.url,tempFileName,userAgent,session)
            if os.path.isfile(tempFileName) == False:
                return
            #TODO handle body text?
            swappedPost = await destinationSub.submit_image(image_path=tempFileName,title=originalPost.title + ' (converted from r/' + originSub.display_name + ')',nsfw=originalPost.over_18)
            os.remove(tempFileName)

        else:
            convertedImages = []
            async with asyncio.TaskGroup() as tg:
                _ = [tg.create_task(processGalleryItem(ii,jj,originalPost,item,destinationSub,session,convertedImages)) for jj,item in enumerate(originalPost.gallery_data['items'])]

            #TODO handle body text?
            swappedPost = await destinationSub.submit_gallery(title=originalPost.title + ' (converted from r/' + originSub.display_name + ')',images=convertedImages,nsfw=originalPost.over_18)

            for image in convertedImages:
                os.remove(image['image_path'])

        async with asyncio.TaskGroup() as tg:
            tg.create_task(swappedPost.reply("Original post: " + originalPost.permalink + " by [" + originalPost.author.name + "](https://reddit.com/user/" + originalPost.author.name + ")"+
                            "\r\n\r\n" +
                            "I'm a bot made by [KRA2008](https://reddit.com/user/KRA2008) to help the stereoscopic 3D community on Reddit :) " +
                            "I convert posts between cross and parallel viewing and repost them between the two subs. " +
                            "Please message [KRA2008](https://reddit.com/user/KRA2008) if you have comments or questions."))
            tg.create_task(originalPost.reply("I'm a bot made by [KRA2008](https://reddit.com/user/KRA2008) and I've converted this post to r/" + destinationSub.display_name + " and you can see that here: " + swappedPost.permalink))

        with open(crossPostedListName,'a') as file:
            if testing:
                print('processed ' + originalPost.id + ' in testing mode')
            else:
                with open(crossPostedListName,'a') as file:
                    file.write(originalPost.id+'\n')
    except Exception as ex:
        print('processPost ex: ' + str(ex))
        raise


def duplicatesFilter(post,destinationPostTitles):
    for title in destinationPostTitles:
        if SequenceMatcher(None, post.title, title).ratio() > 0.8:
            return True
    return False


async def swapAndCrossPost(creds,originSub,destinationSub):
    try:
        postsSearchLimit = 100
        postsMakeLimit = 2 if testing else 10
        print(f'starting {originSub.display_name} to {destinationSub.display_name}')
        originPosts = originSub.new(limit=postsSearchLimit)
        destinationPostTitles = [post.title async for post in destinationSub.new(limit=postsSearchLimit)]

        with open(crossPostedListName,'r') as file:
            crossPosted = file.read()

        eligiblePosts = [post async for post in originPosts 
                        if post.is_video == False and                          #keep videos out for now
                        (hasattr(post,'is_gallery') == True or
                        post.url.endswith('.jpeg') or
                        post.url.endswith('.png') or
                        post.url.endswith('.jpg')) and
                        post.id not in crossPosted and
                        post.author.name not in creds['OptedOutUsers'] and
                        post.author.name != 'StereomancerBot' and
                        post.upvote_ratio > 0.5 and
                        duplicatesFilter(post,destinationPostTitles) == False] #TODO: filter out old stuff too
        print(f'found {len(eligiblePosts)} eligible posts')

        eligiblePosts = eligiblePosts[:postsMakeLimit]
        print(f'converting {len(eligiblePosts)} posts')
        async with ClientSession() as session:
            async with asyncio.TaskGroup() as tg:
                _ = [tg.create_task(processPost(ii,originalPost,originSub,destinationSub,session)) for ii,originalPost in enumerate(eligiblePosts)]
    except Exception as ex:
        print('swapAndCross ex: ' + str(ex))
        raise


async def main():
    try:
        with open(credsFileName,'r') as file:
            creds = json.load(file)

        async with asyncpraw.Reddit(
            client_id=creds['RedditClientId'],
            client_secret=creds['RedditClientSecret'],
            password=creds['RedditPassword'],
            username=creds['RedditUsername'],
            user_agent=userAgent
        ) as reddit:
            
            if testing:
                first = 'test'
                second = 'u_StereomancerBot'
            else:
                first = 'crossview'
                second = 'parallelview'

            async with asyncio.TaskGroup() as tg:
                firstSubredditTask = tg.create_task(reddit.subreddit(first))
                secondSubredditTask = tg.create_task(reddit.subreddit(second))
            firstSubreddit = firstSubredditTask.result()
            secondSubreddit = secondSubredditTask.result()

            async with asyncio.TaskGroup() as tg:
                tg.create_task(swapAndCrossPost(creds,firstSubreddit,secondSubreddit))
                tg.create_task(swapAndCrossPost(creds,secondSubreddit,firstSubreddit))

    except OSError as e:
        print(f"OSError caught: {e}")
        print(f"OSError number (errno): {e.errno}")
        print(f"Operating system error code (winerror on Windows): {getattr(e, 'winerror', 'N/A')}")
        print(f"Error message: {e.strerror}")
    except Exception as e:
        print(f"Error caught: {e}")
        pprint.pprint(vars(e))

asyncio.run(main())