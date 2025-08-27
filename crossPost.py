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

# testing = True
testing = False

crossPostedListName = 'CrossPosted.txt'
credsFileName = 'creds.json'
userAgent = 'windows:com.kra2008.stereomancerbot:v2 (by /u/kra2008)'


async def convertGalleryItem(item,session,sbsImages,anaglyphImages,wigglegramImages,extension,toSecondary,isCross):
    try:
        tempFileBase=f'temp/{uuid.uuid4()}'

        imageUrl = f'https://i.redd.it/{item['media_id']}{extension}'

        await stereoConvert.convertAndSaveToAllFormats(imageUrl,tempFileBase,extension,userAgent,session,toSecondary,isCross)

        if toSecondary:
            sbsImages.append({'image_path':tempFileBase+'sbs'+extension})
        anaglyphImages.append({'image_path':tempFileBase+'anaglyph'+extension})
        wigglegramImages.append({'image_path':tempFileBase+'.gif'})
    except Exception as ex:
        print('processGalleryItems ex: ' + ex)
        pprint.pprint(vars(ex))
        raise


async def convertAndSubmitPost(originalPost,originSub,secondarySub,anaglyphSub,wigglegramSub,session,toSecondary,isCross):
    try:
        # pprint.pprint(vars(originalPost))

        print('converting ' + originalPost.title)
        
        if hasattr(originalPost,'is_gallery') == False:
            baseUrl = urlparse(originalPost.url).path
            f,extension = os.path.splitext(baseUrl)
            tempFileBase = f'temp/{uuid.uuid4()}'
            await stereoConvert.convertAndSaveToAllFormats(originalPost.url,tempFileBase,extension,userAgent,session,toSecondary,isCross)

            async with asyncio.TaskGroup() as tg:
                if toSecondary:
                    secondaryTask = tg.create_task(secondarySub.submit_image(image_path=tempFileBase+'sbs'+extension,title=originalPost.title + ' (converted from r/' + originSub.display_name + ')',nsfw=originalPost.over_18))
                else:
                    secondaryTask = None
                anaglyphTask = tg.create_task(anaglyphSub.submit_image(image_path=tempFileBase+'anaglyph'+extension,title=originalPost.title + ' (converted from r/' + originSub.display_name + ')',nsfw=originalPost.over_18))
                wigglegramTask = tg.create_task(wigglegramSub.submit_image(image_path=tempFileBase+'.gif',title=originalPost.title + ' (converted from r/' + originSub.display_name + ')',nsfw=originalPost.over_18))

            os.remove(tempFileBase+'sbs'+extension)
            os.remove(tempFileBase+'anaglyph'+extension)
            os.remove(tempFileBase+'.gif')

        else:
            sbsImages = []
            anaglyphImages = []
            wigglegramImages = []
            previewUrl = originalPost.media_metadata[originalPost.gallery_data['items'][0]['media_id']]['p'][0]['u']
            baseUrl = urlparse(previewUrl).path
            f,extension = os.path.splitext(baseUrl)
            async with asyncio.TaskGroup() as tg:
                _ = [tg.create_task(convertGalleryItem(item,session,sbsImages,anaglyphImages,wigglegramImages,extension,toSecondary,isCross)) for item in originalPost.gallery_data['items']]


            async with asyncio.TaskGroup() as tg:
                if toSecondary:
                    secondaryTask = tg.create_task(secondarySub.submit_gallery(title=originalPost.title + ' (converted from r/' + originSub.display_name + ')',images=sbsImages,nsfw=originalPost.over_18))
                anaglyphTask = tg.create_task(anaglyphSub.submit_gallery(title=originalPost.title + ' (converted from r/' + originSub.display_name + ')',images=anaglyphImages,nsfw=originalPost.over_18))
                wigglegramTask = tg.create_task(wigglegramSub.submit_gallery(title=originalPost.title + ' (converted from r/' + originSub.display_name + ')',images=wigglegramImages,nsfw=originalPost.over_18))

            for image in sbsImages:
                os.remove(image['image_path'])

        print('converted ' + originalPost.title)

        swap = secondaryTask.result()
        anaglyph = anaglyphTask.result()
        wigglegram = wigglegramTask.result()

        originComment = f'I\'m a bot made by [KRA2008](https://reddit.com/user/KRA2008) and I\'ve converted this post to:'
        if toSecondary:
            sbsSub = 'parallelview' if isCross else 'crossview'
            originComment+= f'\r\n\r\n[{sbsSub}]({swap.permalink})'
        originComment+= f'\r\n\r\n[anaglyph]({anaglyph.permalink})'
        originComment+= f'\r\n\r\n[wigglegram]({wigglegram.permalink})'

        conversionComment = f'[Original post]({originalPost.permalink}) by [{originalPost.author.name}](https://reddit.com/user/{originalPost.author.name})\r\n\r\nI\'m a bot made by [KRA2008](https://reddit.com/user/KRA2008) to help the stereoscopic 3D community on Reddit :) I convert posts between viewing methods and repost them between subs. Please message [KRA2008](https://reddit.com/user/KRA2008) if you have comments or questions.'
        
        async with asyncio.TaskGroup() as itg:
            if swap is not None:
                itg.create_task(swap.reply(conversionComment))
            itg.create_task(anaglyph.reply(conversionComment))
            itg.create_task(wigglegram.reply(conversionComment))
            itg.create_task(originalPost.reply(originComment))
        print('comments made for ' + originalPost.title)

        if testing:
            print('processed ' + originalPost.title + ' in testing mode')
        else:
            with open(crossPostedListName,'a') as file:
                file.write(originalPost.id+'\n')


    except Exception as ex:
        print('convertAndSubmitPost ex: ' + str(ex))
        pprint.pprint(vars(ex))
        raise


def doPostTitlesMatch(post1,post2):
    return SequenceMatcher(None, post1.title, post2.title).ratio() > 0.8


async def checkForDuplicatesAndInitiateConversions(originalPost,primarySub,secondarySub,anaglyphSub,wigglegramSub,session,isCross,secondaryPosts):
    try:
        duplicateFound = False
        async for secondaryPost in secondaryPosts:
            if doPostTitlesMatch(originalPost,secondaryPost):
                duplicateFound = True
                break
        await convertAndSubmitPost(originalPost,primarySub,secondarySub,anaglyphSub,wigglegramSub,session, duplicateFound == False,isCross)
    except Exception as ex:
        print('checkForDuplicatesAndInitiateConversions ex: ' + str(ex))
        pprint.pprint(vars(ex))
        raise

async def convertAndCrossPost(creds,primarySub,secondarySub,anaglyphSub,wigglegramSub,isCross):
    try:
        postsSearchLimit = 100
        postsMakeLimit = 3
        primaryPosts = primarySub.top('day',limit=postsSearchLimit)
        secondaryPosts = secondarySub.top('day',limit=postsSearchLimit)

        with open(crossPostedListName,'r') as file:
            crossPosted = file.read()

        optedOutList = creds['OptedOutUsers']

        primaryPosts = [post async for post in primaryPosts 
                        if post.is_video == False and                          #keep videos out for now
                        hasattr(post,'is_gallery') == False and #TODO: upgrade to fix this bug
                        ('.jpeg' in post.url or
                        '.png' in post.url or
                        '.jpg' in post.url) and
                        post.id not in crossPosted and 
                        post.author.name not in optedOutList and
                        post.author.name != 'StereomancerBot' and
                        post.upvote_ratio > 0.75] #TODO: filter out old stuff too

        print(f'found {len(primaryPosts)} eligible posts from {primarySub.display_name}')

        primaryPosts = primaryPosts[:postsMakeLimit]

        print(f'converting {len(primaryPosts)} from {primarySub.display_name}')

        async with ClientSession() as session:
            async with asyncio.TaskGroup() as tg:
                _ = [tg.create_task(checkForDuplicatesAndInitiateConversions(originalPost,primarySub,secondarySub,anaglyphSub,wigglegramSub,session,isCross,secondaryPosts)) for originalPost in primaryPosts]
                
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
            
            if testing:
                crossview='test'
                parallelview='u_StereomancerBot'
                anaglyph='notcrossview'
                wigglegrams='crappysoftwaredesign'
            else:
                crossview='crossview'
                parallelview='parallelview'
                anaglyph='anaglyph'
                wigglegrams='wigglegrams'

            async with asyncio.TaskGroup() as tg:
                crossviewSubredditTask = tg.create_task(reddit.subreddit(crossview))
                parallelviewSubredditTask = tg.create_task(reddit.subreddit(parallelview))
                anaglyphSubredditTask = tg.create_task(reddit.subreddit(anaglyph))
                wigglegramSubredditTask = tg.create_task(reddit.subreddit(wigglegrams))
            crossviewSubreddit = crossviewSubredditTask.result()
            parallelviewSubreddit = parallelviewSubredditTask.result()
            anaglyphSubreddit = anaglyphSubredditTask.result()
            wigglegramSubreddit = wigglegramSubredditTask.result()

            async with asyncio.TaskGroup() as tg:
                tg.create_task(convertAndCrossPost(creds,crossviewSubreddit,parallelviewSubreddit,anaglyphSubreddit,wigglegramSubreddit,True))
                tg.create_task(convertAndCrossPost(creds,parallelviewSubreddit,crossviewSubreddit,anaglyphSubreddit,wigglegramSubreddit,False))

    except OSError as e:
        print(f"OSError caught: {e}")
        print(f"OSError number (errno): {e.errno}")
        print(f"Operating system error code (winerror on Windows): {getattr(e, 'winerror', 'N/A')}")
        print(f"Error message: {e.strerror}")
    except Exception as e:
        print(f"Error caught: {e}")
        pprint.pprint(vars(e))

asyncio.run(main())