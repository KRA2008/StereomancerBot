import asyncpraw
import json
import pprint
from difflib import SequenceMatcher
import stereoConvert
import os
import asyncio
from aiohttp import ClientSession
import uuid
from urllib.parse import urljoin, urlparse
import dateutil.parser
from datetime import datetime, timedelta, timezone

# isTesting = True
isTesting = False

crossPostedListName = 'CrossPosted.txt'
credsFileName = 'creds.json'
userAgent = 'windows:com.kra2008.stereomancerbot:v2 (by /u/kra2008)'
postsSearchLimit = 100
postsMakeLimit = 3


async def convertGalleryItem(item,session,sbsImages,anaglyphImages,extension,isCross):
    try:
        tempFileBase=f'temp/{uuid.uuid4()}'

        imageUrl = f'https://i.redd.it/{item['media_id']}{extension}'

        await stereoConvert.convertAndSaveToAllFormats(imageUrl,tempFileBase,extension,userAgent,session,isCross)

        sbsImages.append({'image_path':tempFileBase+'sbs'+extension})
        anaglyphImages.append({'image_path':tempFileBase+'anaglyph'+extension})
    except Exception as ex:
        print('processGalleryItems ex: ' + ex)
        pprint.pprint(vars(ex))
        raise


async def convertAndSubmitPost(originalPost,originSub,secondarySub,anaglyphSub,session,secondaryDuplicateFound,anaglyphDuplicateFound,isCross):
    try:
        # pprint.pprint(vars(originalPost))

        print('converting ' + originalPost.title)

        doAnaglyphConversion = True
        if (secondaryDuplicateFound and not isCross) or anaglyphDuplicateFound:
            doAnaglyphConversion = False
        
        if hasattr(originalPost,'is_gallery') == False:
            baseUrl = urlparse(originalPost.url).path
            f,extension = os.path.splitext(baseUrl)
            tempFileBase = f'temp/{uuid.uuid4()}'
            await stereoConvert.convertAndSaveToAllFormats(originalPost.url,tempFileBase,extension,userAgent,session,isCross)

            print('converted ' + originalPost.title + ", submitting")

            async with asyncio.TaskGroup() as tg:
                if not secondaryDuplicateFound:
                    secondaryTask = tg.create_task(secondarySub.submit_image(image_path=tempFileBase+'sbs'+extension,title=originalPost.title + ' (converted from r/' + originSub.display_name + ')',nsfw=originalPost.over_18))
                if doAnaglyphConversion:
                    anaglyphTask = tg.create_task(anaglyphSub.submit_image(image_path=tempFileBase+'anaglyph'+extension,title=originalPost.title + ' (converted from r/' + originSub.display_name + ')',nsfw=originalPost.over_18))
            try:
                os.remove(tempFileBase+'sbs'+extension)
                os.remove(tempFileBase+'anaglyph'+extension)
            except Exception as e:
                print('error while removing: ' + str(e))

        else:
            sbsImages = []
            anaglyphImages = []
            previewUrl = originalPost.media_metadata[originalPost.gallery_data['items'][0]['media_id']]['p'][0]['u']
            baseUrl = urlparse(previewUrl).path
            f,extension = os.path.splitext(baseUrl)
            async with asyncio.TaskGroup() as tg:
                _ = [tg.create_task(convertGalleryItem(item,session,sbsImages,anaglyphImages,extension,isCross)) for item in originalPost.gallery_data['items']]

            print('converted ' + originalPost.title + ", submitting")

            async with asyncio.TaskGroup() as tg:
                if not secondaryDuplicateFound:
                    secondaryTask = tg.create_task(secondarySub.submit_gallery(title=originalPost.title + ' (converted from r/' + originSub.display_name + ')',images=sbsImages,nsfw=originalPost.over_18))
                if doAnaglyphConversion:
                    anaglyphTask = tg.create_task(anaglyphSub.submit_gallery(title=originalPost.title + ' (converted from r/' + originSub.display_name + ')',images=anaglyphImages,nsfw=originalPost.over_18))
                    
            try:
                for image in sbsImages:
                    os.remove(image['image_path'])
                for image in anaglyphImages:
                    os.remove(image['image_path'])
            except Exception as ex:
                print('error removing albums: ' + str(ex))

        if not secondaryDuplicateFound:
            swap = secondaryTask.result()
        if doAnaglyphConversion:
            anaglyph = anaglyphTask.result()

        originComment = f'I\'m a bot made by [KRA2008](https://reddit.com/user/KRA2008) and I\'ve converted this post to:'
        if not secondaryDuplicateFound:
            sbsSub = 'parallelview' if isCross else 'crossview'
            originComment+= f'\r\n\r\n[{sbsSub}]({swap.permalink})'
        if doAnaglyphConversion:
            originComment+= f'\r\n\r\n[anaglyph]({anaglyph.permalink})'

        conversionComment = f'[Original post]({originalPost.permalink}) by [{originalPost.author.name}](https://reddit.com/user/{originalPost.author.name})\r\n\r\nI\'m a bot made by [KRA2008](https://reddit.com/user/KRA2008) to help the stereoscopic 3D community on Reddit :) I convert posts between viewing methods and repost them between subs. Please message [KRA2008](https://reddit.com/user/KRA2008) if you have comments or questions.'
        
        print('beginning comment tasks for ' + originalPost.title)

        async with asyncio.TaskGroup() as itg:
            if not secondaryDuplicateFound:
                itg.create_task(swap.reply(conversionComment))
            if doAnaglyphConversion:
                itg.create_task(anaglyph.reply(conversionComment))
            itg.create_task(originalPost.reply(originComment))
        print('comments made for ' + originalPost.title)

        if isTesting:
            print('processed ' + originalPost.title + ' in testing mode')
        else:
            with open(crossPostedListName,'a') as file:
                file.write(originalPost.id+'\n')


    except Exception as ex:
        print('convertAndSubmitPost ex: ' + str(ex))
        pprint.pprint(vars(ex))
        raise


def doPostTitlesMatch(post1,post2):
    titleLength = min(len(post1.title),len(post2.title))
    threshold = titleLength/(3+titleLength) #plotted length against ratio while allowing ' (OC)' tacked on the end
    matchRatio = SequenceMatcher(None, post1.title, post2.title).ratio()
    if matchRatio > threshold:
        try:
            date1 = dateutil.parser.parse(post1.title, fuzzy=True)
            date2 = dateutil.parser.parse(post2.title, fuzzy=True)
            if date1 == date2: #allow fractals with date inside
                return True
            else:
                return False
        except Exception as ex:
            return True
    else:
        return False


async def checkForDuplicatesAndInitiateConversions(originalPost,primarySub,secondarySub,anaglyphSub,session,isCross):
    try:
        secondaryPosts = secondarySub.new(limit=postsSearchLimit)
        anaglyphPosts = anaglyphSub.new(limit=postsSearchLimit)

        secondaryDuplicateFound = False
        async for secondaryPost in secondaryPosts:
            if doPostTitlesMatch(originalPost,secondaryPost):
                secondaryDuplicateFound = True
                break
            
        anaglyphDuplicateFound = False
        async for anaglyphPost in anaglyphPosts:
            if doPostTitlesMatch(originalPost,anaglyphPost):
                anaglyphDuplicateFound = True
                break

        if secondaryDuplicateFound and anaglyphDuplicateFound:
            return
        
        if secondaryDuplicateFound and not isCross:
            return
        
        await convertAndSubmitPost(originalPost,primarySub,secondarySub,anaglyphSub,session, secondaryDuplicateFound,anaglyphDuplicateFound,isCross)
    except Exception as ex:
        print('checkForDuplicatesAndInitiateConversions ex: ' + str(ex))
        pprint.pprint(vars(ex))
        raise

async def convertAndCrossPost(creds,primarySub,secondarySub,anaglyphSub,isCross):
    try:
        primaryPosts = primarySub.top('week',limit=postsSearchLimit)

        with open(crossPostedListName,'r') as file:
            crossPosted = file.read()

        optedOutList = creds['OptedOutUsers']

        primaryPosts = [post async for post in primaryPosts 
                        if post.is_video == False and                          #keep videos out for now
                        (hasattr(post,'is_gallery') == True or
                        ('.jpeg' in post.url or
                        '.png' in post.url or
                        '.jpg' in post.url)) and
                        post.id not in crossPosted and 
                        post.author.name not in optedOutList and
                        post.author.name != 'StereomancerBot' and
                        post.upvote_ratio > 0.75 and
                        datetime.now(timezone.utc) - timedelta(days=1) > datetime.fromtimestamp(post.created_utc,tz=timezone.utc)]

        print(f'found {len(primaryPosts)} eligible posts from {primarySub.display_name}')

        primaryPosts = primaryPosts[:postsMakeLimit]

        print(f'converting {len(primaryPosts)} from {primarySub.display_name}')

        if isTesting:
            print("testing. not converting")
        else:
            async with ClientSession() as session:
                async with asyncio.TaskGroup() as tg:
                    _ = [tg.create_task(checkForDuplicatesAndInitiateConversions(originalPost,primarySub,secondarySub,anaglyphSub,session,isCross)) for originalPost in primaryPosts]
                
    except Exception as ex:
        print('convertAndCrossPost ex: ' + str(ex))
        pprint.pprint(vars(ex))
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
            
            if isTesting:
                crossview='crossview'
                parallelview='parallelview'
                anaglyph='anaglyph'
            else:
                crossview='crossview'
                parallelview='parallelview'
                anaglyph='anaglyph'

            async with asyncio.TaskGroup() as tg:
                crossviewSubredditTask = tg.create_task(reddit.subreddit(crossview))
                parallelviewSubredditTask = tg.create_task(reddit.subreddit(parallelview))
                anaglyphSubredditTask = tg.create_task(reddit.subreddit(anaglyph))
            crossviewSubreddit = crossviewSubredditTask.result()
            parallelviewSubreddit = parallelviewSubredditTask.result()
            anaglyphSubreddit = anaglyphSubredditTask.result()

            async with asyncio.TaskGroup() as tg:
                tg.create_task(convertAndCrossPost(creds,crossviewSubreddit,parallelviewSubreddit,anaglyphSubreddit,True))
                tg.create_task(convertAndCrossPost(creds,parallelviewSubreddit,crossviewSubreddit,anaglyphSubreddit,False))

    except OSError as e:
        print(f"OSError caught: {e}")
        print(f"OSError number (errno): {e.errno}")
        print(f"Operating system error code (winerror on Windows): {getattr(e, 'winerror', 'N/A')}")
        print(f"Error message: {e.strerror}")
    except Exception as e:
        print(f"Error caught: {e}")
        pprint.pprint(vars(e))

asyncio.run(main())