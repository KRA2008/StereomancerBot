import praw
import json
import stereoConvert

try:
    with open('creds.json','r') as file:
        creds = json.load(file)

    swappedListName = 'Swapped.txt'
    with open(swappedListName,'r') as file:
        swappedList = file.read()

    reddit = praw.Reddit(
        client_id=creds['RedditClientId'],
        client_secret=creds['RedditClientSecret'],
        password=creds['RedditPassword'],
        username=creds['RedditUsername'],
        user_agent="windows:com.kra2008.stereomancerbot:v2 (by /u/kra2008)"
    )

    def swapSidesAndUpload(post):
        selfSub = reddit.subreddit('u_StereomancerBot')
        if hasattr(post,'is_gallery') == False:
            tempFileName='temp/swapTemp.jpg'
            stereoConvert.convertImage(post.url,tempFileName)

            return selfSub.submit_image(title=f'{post.title}(originally by {post.author.name}, with sides swapped)',image_path=tempFileName,nsfw=post.over_18)
        else:
            convertedImages = []
            for ii,item in enumerate(post.gallery_data['items']):
                tempFileName=f'temp/swapTemp{ii}.jpg'
                stereoConvert.convertImage(f'https://i.redd.it/{item['media_id']}.jpg',tempFileName)
                convertedImages.append({'image_path':tempFileName})
                
            return selfSub.submit_gallery(title=f'{post.title}(originally by {post.author.name}, with sides swapped)',images=convertedImages,nsfw=post.over_18)

    def checkForSwaps(subredditName):
        maxPostsSearch=100
        posts = reddit.subreddit(subredditName).new(limit=maxPostsSearch)
        posts = [post for post in posts 
                if post.is_video == False and          #keep videos out for now
                post.id not in swappedList and
                (hasattr(post,'is_gallery') == True or
                post.url.endswith('.jpeg') or
                post.url.endswith('.png') or
                post.url.endswith('.jpg'))]

        for post in posts:
            for comment in post.comments.list():
                if comment.body == '!swap':
                    fixedPost = swapSidesAndUpload(post)

                    fixedPost.reply(f'I\'m a bot made by [KRA2008](https://reddit.com/user/KRA2008) and I\'ve swapped the sides of this post and you can see the original here: {post.permalink}')

                    post.reply(f'I\'m a bot made by [KRA2008](https://reddit.com/user/KRA2008) and I\'ve swapped the sides of this post and you can see that here: {fixedPost.url}' +
                               '\n\n' +
                               'Sometimes people accidentally post a stereogram using the wrong viewing method, so I\'m here to easily fix that. Don\'t worry, it\'s such a common mistake that there\'s a bot to fix it. :)' +
                               '\n\n'
                               'It\'s probably a good time to make sure you\'re really viewing the way you think you are by checking out [this tester image](https://i.redd.it/g5ilwgk99r781.jpg). ' +
                               'Feel free to message [KRA2008](https://reddit.com/user/KRA2008) with any questions you may have.')
                                
                    with open(swappedListName,'a') as file:
                        file.write(post.id+'\n')

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