import asyncpraw
import json
import stereoConvert
import asyncio
import os
from urllib.parse import urlparse
import pprint
from aiohttp import ClientSession

swappedListName = 'Swapped.txt'
credsFileName = 'creds.json'
userAgent = 'windows:com.kra2008.stereomancerbot:v2 (by /u/kra2008)'

async def main():
    try:
        with open(credsFileName,'r') as file:
            creds = json.load(file)

        with open(swappedListName,'r') as file:
            swappedList = file.read()

        reddit = asyncpraw.Reddit(
            client_id=creds['RedditClientId'],
            client_secret=creds['RedditClientSecret'],
            password=creds['RedditPassword'],
            username=creds['RedditUsername'],
            user_agent=userAgent
        )

        async def swapSidesAndUpload(post):
            selfSub = await reddit.subreddit('u_StereomancerBot')
            async with ClientSession() as session:
                if hasattr(post,'is_gallery') == False:
                    print('converting ' + post.title)
                    f,extension = os.path.splitext(post.url)
                    tempFileName=f'temp/swapTemp{extension}'
                    await stereoConvert.downloadAndSwapSides(post.url,tempFileName,userAgent,session)
                    newImage = await selfSub.submit_image(title=f'{post.title}(originally by {post.author.name}, with sides swapped)',image_path=tempFileName,nsfw=post.over_18)
                    os.remove(tempFileName)
                    return newImage
                else:
                    print('converting ' + post.title)
                    convertedImages = []
                    previewUrl = post.media_metadata[post.gallery_data['items'][0]['media_id']]['p'][0]['u']
                    baseUrl = urlparse(previewUrl).path
                    f,extension = os.path.splitext(baseUrl)
                    for ii,item in enumerate(post.gallery_data['items']):
                        tempFileName=f'temp/swapTemp{ii}{extension}'
                        await stereoConvert.downloadAndSwapSides(f'https://i.redd.it/{item['media_id']}{extension}',tempFileName,userAgent,session)
                        convertedImages.append({'image_path':tempFileName})
                    
                    newGallery = await selfSub.submit_gallery(title=f'{post.title} (originally by {post.author.name}, with sides swapped)',images=convertedImages,nsfw=post.over_18)
                    for image in convertedImages:
                        os.remove(image['image_path'])
                    return newGallery

        async def checkForSwaps(subredditName):
            maxPostsSearch=100
            print('checking ' + subredditName)
            posts = (await reddit.subreddit(subredditName)).new(limit=maxPostsSearch)
            posts = [post async for post in posts 
                    if post.is_video == False and          #keep videos out for now
                    post.id not in swappedList and
                    (hasattr(post,'is_gallery') == True or
                    post.url.endswith('.jpeg') or
                    post.url.endswith('.png') or
                    post.url.endswith('.jpg'))]

            for post in posts:
                await post.load()
                for comment in post.comments.list():
                    if comment.body == '!swap':
                        fixedPost = await swapSidesAndUpload(post)

                        await fixedPost.reply(f'I\'m a bot made by [KRA2008](https://reddit.com/user/KRA2008) and I\'ve swapped the sides of this post and you can see the original here: {post.permalink}')

                        await post.reply(f'I\'m a bot made by [KRA2008](https://reddit.com/user/KRA2008) and I\'ve swapped the sides of this post and you can see that here: {fixedPost.url}' +
                                '\n\n' +
                                'Sometimes people accidentally post a stereogram using the wrong viewing method, so I\'m here to easily fix that. Don\'t worry, it\'s such a common mistake that there\'s a bot to fix it. :)' +
                                '\n\n'
                                'It\'s probably a good time to make sure you\'re really viewing the way you think you are by checking out [this tester image](https://i.redd.it/g5ilwgk99r781.jpg). ' +
                                'Feel free to message [KRA2008](https://reddit.com/user/KRA2008) with any questions you may have.')
                                    
                        with open(swappedListName,'a') as file:
                            file.write(post.id+'\n')

        await checkForSwaps('crossview')
        await checkForSwaps('parallelview')
        # await checkForSwaps('test')
    except OSError as e:
        print(f"OSError caught: {e}")
        print(f"OSError number (errno): {e.errno}")
        print(f"Operating system error code (winerror on Windows): {getattr(e, 'winerror', 'N/A')}")
        print(f"Error message: {e.strerror}")
    except Exception as e:
        print(f"Error caught: {e}")
        pprint.pprint(vars(e))

asyncio.run(main())