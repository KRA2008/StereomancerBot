import asyncpraw
import json
import pprint
from difflib import SequenceMatcher
import stereoConvert
import os
import asyncio
from aiohttp import ClientSession
from urllib.parse import urlparse
import uuid

# testing = True
testing = False

sbsCrossPostedListName = 'SbsCrossPosted.txt'
anaglyphCrossPostedListName = 'AnaglyphCrossPosted.txt'
credsFileName = 'creds.json'
userAgent = 'windows:com.kra2008.stereomancerbot:v2 (by /u/kra2008)'


async def processGalleryItem(ii,jj,item,destinationSub,session,convertedImages,extension,isCross,isAnaglyph):
    try:
        tempFileName=f'temp/{uuid.uuid4()}{extension}'
        imageUrl = f'https://i.redd.it/{item['media_id']}{extension}'
        if isAnaglyph:
            await stereoConvert.convertSbsToAnaglyph(imageUrl,tempFileName,userAgent,session,isCross)
        else:
            await stereoConvert.swapCrossParallel(imageUrl,tempFileName,userAgent,session)
        if os.path.isfile(tempFileName) == False:
            return
        convertedImages.append({'image_path':tempFileName})
    except Exception as ex:
        print('processGalleryItems ex: ' + ex)
        pprint.pprint(vars(ex))
        raise


async def processPost(ii,originalPost,originSub,destinationSub,session,isCross,isAnaglyph):
    try:
        print(f'{originalPost.title}, {originalPost.id}')
        # pprint.pprint(vars(originalPost))

        if hasattr(originalPost,'is_gallery') == False:
            f,extension = os.path.splitext(originalPost.url)
            tempFileName=f'temp/{uuid.uuid4()}{extension}'
            if isAnaglyph:
                await stereoConvert.convertSbsToAnaglyph(originalPost.url,tempFileName,userAgent,session,isCross)
            else:
                await stereoConvert.swapCrossParallel(originalPost.url,tempFileName,userAgent,session)
            if os.path.isfile(tempFileName) == False:
                return
            #TODO handle body text?
            swappedPost = await destinationSub.submit_image(image_path=tempFileName,title=originalPost.title + ' (converted from r/' + originSub.display_name + ')',nsfw=originalPost.over_18)
            os.remove(tempFileName)

        else:
            convertedImages = []
            previewUrl = originalPost.media_metadata[originalPost.gallery_data['items'][0]['media_id']]['p'][0]['u']
            baseUrl = urlparse(previewUrl).path
            f,extension = os.path.splitext(baseUrl)
            async with asyncio.TaskGroup() as tg:
                _ = [tg.create_task(processGalleryItem(ii,jj,item,destinationSub,session,convertedImages,extension,isCross,isAnaglyph)) for jj,item in enumerate(originalPost.gallery_data['items'])]

            #TODO handle body text?
            swappedPost = await destinationSub.submit_gallery(title=originalPost.title + ' (converted from r/' + originSub.display_name + ')',images=convertedImages,nsfw=originalPost.over_18)

            for image in convertedImages:
                os.remove(image['image_path'])

        async with asyncio.TaskGroup() as tg:
            tg.create_task(swappedPost.reply("Original post: " + originalPost.permalink + " by [" + originalPost.author.name + "](https://reddit.com/user/" + originalPost.author.name + ")"+
                            "\r\n\r\n" +
                            "I'm a bot made by [KRA2008](https://reddit.com/user/KRA2008) to help the stereoscopic 3D community on Reddit :) " +
                            "I convert posts between viewing methods and repost them between subs. " +
                            "Please message [KRA2008](https://reddit.com/user/KRA2008) if you have comments or questions."))
            tg.create_task(originalPost.reply("I'm a bot made by [KRA2008](https://reddit.com/user/KRA2008) and I've converted this post to r/" + destinationSub.display_name + " and you can see that here: " + swappedPost.permalink))

            if testing:
                print('processed ' + originalPost.id + ' in testing mode')
            else:
                fileToOpen = anaglyphCrossPostedListName if isAnaglyph else sbsCrossPostedListName
                with open(fileToOpen,'a') as file:
                    file.write(originalPost.id+'\n')
    except Exception as ex:
        print('processPost ex: ' + str(ex))
        pprint.pprint(vars(ex))
        raise


def duplicatesFilter(post,checkPosts):
    for checkPost in checkPosts:
        if doPostTitlesMatch(post,checkPost):
            return True
    return False


def doPostTitlesMatch(post1,post2):
    return SequenceMatcher(None, post1.title, post2.title).ratio() > 0.8


async def swapAndCrossPost(creds,originSub,destinationSub,crossCheckSub,isCross,isAnaglyph):
    try:
        postsSearchLimit = 100
        if isAnaglyph:
            postsMakeLimit = 1 if testing else 3
        else:
            postsMakeLimit = 2 if testing else 5
        print(f'starting {originSub.display_name} to {destinationSub.display_name}')
        originPosts = originSub.top('day',limit=postsSearchLimit)
        destinationPosts = [post async for post in destinationSub.top('day',limit=postsSearchLimit)]

        crossPostedFileToOpen = anaglyphCrossPostedListName if isAnaglyph else sbsCrossPostedListName
        with open(crossPostedFileToOpen,'r') as file:
            crossPosted = file.read()

        optedOutList = creds['AnaglyphOptedOutUsers'] if isAnaglyph else creds['SbsOptedOutUsers']

        eligiblePosts = [post async for post in originPosts 
                        if post.is_video == False and                          #keep videos out for now
                        hasattr(post,'is_gallery') == False and #TODO: upgrade to fix this bug
                        (post.url.endswith('.jpeg') or
                        post.url.endswith('.png') or
                        post.url.endswith('.jpg')) and
                        post.id not in crossPosted and 
                        post.author.name not in optedOutList and
                        post.author.name != 'StereomancerBot' and
                        post.upvote_ratio > 0.75] #TODO: filter out old stuff too
        
        if isAnaglyph and crossCheckSub is None == False:
            crossCheckedNonDuplicates = []
            crossCheckPosts = [post async for post in crossCheckSub.top('day',limit=postsSearchLimit)]
            for eligiblePost in eligiblePosts:
                duplicateFound = False
                for crossCheckPost in crossCheckPosts:
                    if doPostTitlesMatch(eligiblePost, crossCheckPost):
                        duplicateFound = True
                        if eligiblePost.created_utc < crossCheckPost.created_utc:
                            crossCheckedNonDuplicates.append(eligiblePost)
                        break
                if duplicateFound == False:
                    crossCheckedNonDuplicates.append(eligiblePost)

            eligiblePosts = crossCheckedNonDuplicates
        else:
            eligiblePosts = [post for post in eligiblePosts
                            if duplicatesFilter(post,destinationPosts) == False]
        
        print(f'found {len(eligiblePosts)} eligible posts in {originSub.display_name} to {destinationSub.display_name}')

        eligiblePosts = eligiblePosts[:postsMakeLimit]
        print(f'converting {len(eligiblePosts)} posts from {originSub.display_name} to {destinationSub.display_name}')
        async with ClientSession() as session:
            async with asyncio.TaskGroup() as tg:
                _ = [tg.create_task(processPost(ii,originalPost,originSub,destinationSub,session,isCross,isAnaglyph)) for ii,originalPost in enumerate(eligiblePosts)]
    except Exception as ex:
        print('swapAndCross ex: ' + str(ex))
        pprint.pprint(vars(ex))
        raise


async def crossPost():
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
                first='test'
                second='u_StereomancerBot'
                third='notcrossview'
            else:
                first='crossview'
                second='parallelview'
                third='anaglyph'

            async with asyncio.TaskGroup() as tg:
                firstSubredditTask = tg.create_task(reddit.subreddit(first))
                secondSubredditTask = tg.create_task(reddit.subreddit(second))
                thirdSubredditTask = tg.create_task(reddit.subreddit(third))
            firstSubreddit = firstSubredditTask.result()
            secondSubreddit = secondSubredditTask.result()
            thirdSubreddit = thirdSubredditTask.result()

            async with asyncio.TaskGroup() as tg:
                tg.create_task(swapAndCrossPost(creds,firstSubreddit,secondSubreddit,None,True,False))
                tg.create_task(swapAndCrossPost(creds,secondSubreddit,firstSubreddit,None,False,False))
                tg.create_task(swapAndCrossPost(creds,firstSubreddit,thirdSubreddit,secondSubreddit,True,True))
                tg.create_task(swapAndCrossPost(creds,secondSubreddit,thirdSubreddit,firstSubreddit,False,True))

    except OSError as e:
        print(f"OSError caught: {e}")
        print(f"OSError number (errno): {e.errno}")
        print(f"Operating system error code (winerror on Windows): {getattr(e, 'winerror', 'N/A')}")
        print(f"Error message: {e.strerror}")
    except Exception as e:
        print(f"Error caught: {e}")
        pprint.pprint(vars(e))

asyncio.run(crossPost())