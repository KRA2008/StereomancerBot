from PIL import Image
from io import BytesIO
from aiohttp import ClientSession


maxImageWidth = 2000


async def downloadAndDownsizeImage(imageUrl,userAgent,session):
    print(f'fetching {imageUrl}')
    headers = {
        'User-Agent':userAgent #required by imgur
    }
    async with session.get(url=imageUrl,headers=headers) as response:
        responseResult = await response.read()
        if response.status != 200:
            print('image fetching failed: ' + str(response.status))
            return #throw?
        downloadedImage = Image.open(BytesIO(responseResult))

    if downloadedImage.width > maxImageWidth:
        downloadedImage = downloadedImage.resize((int(maxImageWidth),int(maxImageWidth * downloadedImage.height / downloadedImage.width)))

    return downloadedImage


async def swapCrossParallel(imageUrl,imagePath,userAgent,session):
    originalImage = await downloadAndDownsizeImage(imageUrl,userAgent,session)

    swappedImage = Image.new(mode=originalImage.mode,size=originalImage.size)

    leftStart = (int(originalImage.width/-2),0)
    rightStart = (int(originalImage.width/2),0)
    swappedImage.paste(originalImage,leftStart)
    swappedImage.paste(originalImage,rightStart)

    if swappedImage.mode in ('RGBA','P'):
        swappedImage = swappedImage.convert('RGB')

    print(f'saving to {imagePath}')
    swappedImage.save(imagePath)
    print(f'saved {imagePath}')


async def convertToAnaglyph(imageUrl,imagePath,userAgent,session):
    originalImage = await downloadAndDownsizeImage(imageUrl,userAgent,session)
    
    newImageWidth = originalImage.width/2
    leftImage = Image.new('RGB',(int(newImageWidth),originalImage.height))
    rightImage = Image.new('RGB',(int(newImageWidth),originalImage.height))

    leftImage.paste(originalImage,(0,0))
    rl,gl,bl = leftImage.split()

    rightImage.paste(originalImage,(int(-newImageWidth),0))
    rr,gr,br = rightImage.split()

    newImage = Image.merge('RGB',(rr,gl,bl))

    print(f'saving to {imagePath}')
    newImage.save(imagePath)
    print(f'saved {imagePath}')