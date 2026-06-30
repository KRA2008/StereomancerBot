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
import logging
import tempfile
from asyncpraw.models import PostMedia
import copy

logger = logging.getLogger(__name__)

isTesting = True
#isTesting = False

credsFileName = 'Creds.json'
userAgent = 'windows:com.kra2008.stereomancerbot:v2 (by /u/kra2008)'
primaryPostsSearchLimit = 100
secondaryPostsSearchLimit = 1000
postsMakeLimit = 2
tempDir = tempfile.gettempdir()

async def convertGalleryItem(item,session,sbsImages,anaglyphImages,extension,isCross):
    try:
        tempFileBase=tempDir + f'/{uuid.uuid4()}'

        imageUrl = f'https://i.redd.it/{item['media_id']}{extension}'

        await stereoConvert.convertAndSaveToAllFormats(imageUrl,tempFileBase,extension,userAgent,session,isCross)

        sbsImage = copy.deepcopy(item)
        sbsImage['media'] = PostMedia(tempFileBase+'sbs'+extension)

        anaglyphImage = copy.deepcopy(item)
        anaglyphImage['media'] = PostMedia(tempFileBase+'anaglyph'+extension)

        sbsImages.append(sbsImage)
        anaglyphImages.append(anaglyphImage)
    except Exception as ex:
        logger.info('convertGalleryItem ex: ' + ex)
        pprint.pprint(vars(ex))
        raise


async def convertAndSubmitPost(originalPost,originSub,secondarySub,anaglyphSub,session,secondaryDuplicateFound,anaglyphDuplicateFound,isCross):
    try:
        logger.info('converting ' + originalPost.title + ' from ' + originSub.display_name)

        doAnaglyphConversion = True
        if (secondaryDuplicateFound and not isCross) or anaglyphDuplicateFound:
            doAnaglyphConversion = False
        
        selfTextStart = f"This is a conversion of [this original post]({originalPost.permalink}) from r/{originSub.display_name} by [{originalPost.author.name}](https://reddit.com/user/{originalPost.author.name}). "
        selfTextEnd = f"Visit [the original post]({originalPost.permalink}) for more information or to leave enthusiastic comments for the original poster.\r\n\r\n"
        selfTextBot = f"*I'm a bot but I am not AI, and I was made by [KRA2008](https://reddit.com/user/KRA2008) without AI. I exist to create a bridge between people with different viewing preferences and abilities. I'm trying to enrich your experience, not make money. Message [KRA2008](https://reddit.com/user/KRA2008) if you have questions or comments about this bot.*"
        if originalPost.selftext != '':
            selfTextQuote = selfTextStart + f"\r\n\r\nThey said:\r\n\r\n> {originalPost.selftext.replace('\n','\n> ')}\r\n\r\n" + selfTextEnd + selfTextBot
        else:
            selfTextQuote = selfTextStart + selfTextEnd + selfTextBot

        if hasattr(originalPost,'is_gallery') == False:
            baseUrl = urlparse(originalPost.url).path
            f,extension = os.path.splitext(baseUrl)
            tempFileBase=tempDir + f'/{uuid.uuid4()}'
            await stereoConvert.convertAndSaveToAllFormats(originalPost.url,tempFileBase,extension,userAgent,session,isCross)

            logger.info('converted ' + originalPost.title + ", submitting")

            async with asyncio.TaskGroup() as tg:
                if not secondaryDuplicateFound:
                    secondaryTask = tg.create_task(secondarySub.submit(image=PostMedia(tempFileBase+'sbs'+extension),title=originalPost.title + ' (converted from r/' + originSub.display_name + ')',nsfw=originalPost.over_18,selftext=selfTextQuote))
                if doAnaglyphConversion:
                    anaglyphTask = tg.create_task(anaglyphSub.submit(image=PostMedia(tempFileBase+'anaglyph'+extension),title=originalPost.title + ' (converted from r/' + originSub.display_name + ')',nsfw=originalPost.over_18,selftext=selfTextQuote))
            try:
                os.remove(tempFileBase+'sbs'+extension)
                os.remove(tempFileBase+'anaglyph'+extension)
            except Exception as e:
                logger.info('error while removing: ' + str(e))

        else:
            sbsImages = []
            anaglyphImages = []
            previewUrl = originalPost.media_metadata[originalPost.gallery_data['items'][0]['media_id']]['p'][0]['u']
            baseUrl = urlparse(previewUrl).path
            f,extension = os.path.splitext(baseUrl)
            async with asyncio.TaskGroup() as tg:
                _ = [tg.create_task(convertGalleryItem(item,session,sbsImages,anaglyphImages,extension,isCross)) for item in originalPost.gallery_data['items']]

            logger.info('converted ' + originalPost.title + ", submitting")

            async with asyncio.TaskGroup() as tg:
                if not secondaryDuplicateFound:
                    secondaryTask = tg.create_task(secondarySub.submit(title=originalPost.title + ' (converted from r/' + originSub.display_name + ')',gallery=sbsImages,nsfw=originalPost.over_18,selftext=selfTextQuote))
                if doAnaglyphConversion:
                    anaglyphTask = tg.create_task(anaglyphSub.submit(title=originalPost.title + ' (converted from r/' + originSub.display_name + ')',gallery=anaglyphImages,nsfw=originalPost.over_18,selftext=selfTextQuote))

            try:
                for image in sbsImages:
                    os.remove(image['image_path'])
                for image in anaglyphImages:
                    os.remove(image['image_path'])
            except Exception as ex:
                logger.info('error removing albums: ' + str(ex))

        if not secondaryDuplicateFound:
            swap = secondaryTask.result()
        if doAnaglyphConversion:
            anaglyph = anaglyphTask.result()

        originComment = f'I\'ve converted this post to:'
        if not secondaryDuplicateFound:
            sbsSub = 'parallelview' if isCross else 'crossview'
            originComment+= f'\r\n\r\n[{sbsSub}]({swap.permalink})'
        if doAnaglyphConversion:
            originComment+= f'\r\n\r\n[anaglyph]({anaglyph.permalink})'
        originComment+= f'\r\n\r\n{selfTextBot}'

        conversionComment = selfTextStart + selfTextEnd + selfTextBot
        
        logger.info('beginning comment tasks for ' + originalPost.title)

        async with asyncio.TaskGroup() as itg:
            if not secondaryDuplicateFound:
                itg.create_task(swap.reply(conversionComment))
            if doAnaglyphConversion:
                itg.create_task(anaglyph.reply(conversionComment))
            itg.create_task(originalPost.reply(originComment))
        logger.info('comments made for ' + originalPost.title)


    except Exception as ex:
        logger.info('convertAndSubmitPost ex: ' + str(ex))
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

async def convertAndCrossPost(creds,primarySub,secondarySub,anaglyphSub,session,isCross):
    try:
        primaryPosts = primarySub.top(time_filter='week',limit=primaryPostsSearchLimit)

        optedOutList = creds['OptedOutUsers']

        primaryPosts = [post async for post in primaryPosts 
                        if post.is_video == False and    #keep videos out for now
                        (hasattr(post,'is_gallery') == True or
                        ('.jpeg' in post.url or
                        '.png' in post.url or
                        '.jpg' in post.url)) and
                        post.author != None and
                        post.author.name not in optedOutList and
                        post.author.name != 'StereomancerBot' and
                        post.upvote_ratio > 0.75 and
                        datetime.now(timezone.utc) - timedelta(days=1) > datetime.fromtimestamp(post.created_utc,tz=timezone.utc)]
                        
        tempPosts = []
        for post in primaryPosts:
            await post.load()
            postIsProcessed = False
            for comment in post.comments:
                if (comment.author != None and
                    comment.author.name == 'StereomancerBot'):
                    postIsProcessed = True
                    break
            if (not postIsProcessed):
                tempPosts.append(post)
        primaryPosts = tempPosts

        logger.info(f'found {len(primaryPosts)} eligible posts from {primarySub.display_name}')

        secondaryPosts = [post async for post in secondarySub.new(limit=secondaryPostsSearchLimit)]
        anaglyphPosts = [post async for post in anaglyphSub.new(limit=secondaryPostsSearchLimit)]
        
        postsCount = 0
        for originalPost in primaryPosts:

            secondaryDuplicateFound = False
            for secondaryPost in secondaryPosts:
                if doPostTitlesMatch(originalPost,secondaryPost):
                    secondaryDuplicateFound = True
                    break
                
            anaglyphDuplicateFound = False
            for anaglyphPost in anaglyphPosts:
                if doPostTitlesMatch(originalPost,anaglyphPost):
                    anaglyphDuplicateFound = True
                    break

            if secondaryDuplicateFound and anaglyphDuplicateFound:
                logger.info('skipping ' + originalPost.title + ', fully processed by OP')
                continue
            
            if secondaryDuplicateFound and not isCross:
                logger.info('skipping ' + originalPost.title + ', swapped by OP')
                continue
            
            postsCount = postsCount + 1
            if (postsCount > postsMakeLimit): 
                return

            await convertAndSubmitPost(originalPost,primarySub,secondarySub,anaglyphSub,session,secondaryDuplicateFound,anaglyphDuplicateFound,isCross)
                
    except Exception as ex:
        logger.info('convertAndCrossPost ex: ' + str(ex))
        pprint.pprint(vars(ex))
        raise


async def main():
    try:
        logger.info('working directory: ' + tempDir)

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
                crossview='test'
                parallelview='testposting'
                anaglyph='testingground4bots'
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

            async with ClientSession() as session:
                async with asyncio.TaskGroup() as tg:
                    tg.create_task(convertAndCrossPost(creds,crossviewSubreddit,parallelviewSubreddit,anaglyphSubreddit,session,True))
                    tg.create_task(convertAndCrossPost(creds,parallelviewSubreddit,crossviewSubreddit,anaglyphSubreddit,session,False))

    except OSError as e:
        logger.info(f"OSError caught: {e}")
        logger.info(f"OSError number (errno): {e.errno}")
        logger.info(f"Operating system error code (winerror on Windows): {getattr(e, 'winerror', 'N/A')}")
        logger.info(f"Error message: {e.strerror}")
    except ExceptionGroup as e:
        logger.info(f"Exception group caught: {e}")
        digIntoExGroup(e)
    except Exception as e:
        logger.info(f"Exception: {e}")
        pprint.pprint(vars(e))

def digIntoExGroup(ex):
    for innerEx in ex.exceptions:
        logger.info(f"Inner exception: {innerEx}")
        if(isinstance(innerEx,ExceptionGroup)):
            digIntoExGroup(innerEx)