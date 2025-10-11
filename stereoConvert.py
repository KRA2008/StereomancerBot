from PIL import Image
from io import BytesIO


async def downloadAndDownsizeImage(imageUrl,userAgent,session):
    maxImageWidth = 2000
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


async def convertAndSaveToAllFormats(imageUrl,imageBasePath,extension,userAgent,session,isCross):
    originalImage = await downloadAndDownsizeImage(imageUrl,userAgent,session)
    swapCrossParallel(originalImage,imageBasePath,extension)
    convertSbsToAnaglyph(originalImage,imageBasePath,extension,isCross)


async def downloadAndSwapSides(imageUrl,imageBasePath,extension,userAgent,session):
    originalImage = await downloadAndDownsizeImage(imageUrl,userAgent,session)
    swapCrossParallel(originalImage,imageBasePath,extension)


def swapCrossParallel(originalImage,destinationBasePath,extension):
    swappedImage = Image.new(mode=originalImage.mode,size=originalImage.size)

    leftStart = (int(originalImage.width/-2),0)
    rightStart = (int(originalImage.width/2),0)
    swappedImage.paste(originalImage,leftStart)
    swappedImage.paste(originalImage,rightStart)

    if swappedImage.mode in ('RGBA','P'):
        swappedImage = swappedImage.convert('RGB')

    swappedImage.save(destinationBasePath+'sbs'+extension)


def convertSbsToAnaglyph(originalImage,destinationBasePath,extension,isCross):
    anaglyphWidth = originalImage.width/2
    side1 = Image.new('RGB',(int(anaglyphWidth),originalImage.height))
    side2 = Image.new('RGB',(int(anaglyphWidth),originalImage.height))

    side1.paste(originalImage,(0,0))
    r1,g1,b1 = side1.split()

    side2.paste(originalImage,(int(-anaglyphWidth),0))
    r2,g2,b2 = side2.split()

    if isCross:
        anaglyphImage = Image.merge('RGB',(r2,g1,b1))
    else:
        anaglyphImage = Image.merge('RGB',(r1,g2,b2))

    anaglyphImage.save(destinationBasePath+'anaglyph'+extension)


def convertSbsToWigglegram(originalImage,destinationBasePath):
    wigglegramWidth = originalImage.width/2
    frame1 = Image.new('RGB',(int(wigglegramWidth),originalImage.height))
    frame2 = Image.new('RGB',(int(wigglegramWidth),originalImage.height))

    frame1.paste(originalImage,(0,0))
    frame2.paste(originalImage,(int(-wigglegramWidth),0))

    frame1.save(destinationBasePath+'.gif', save_all=True, append_images=[frame2,frame1], duration=150, loop=0)


def convertSbsToSeparate(originalImage,destinationBasePath,extension):
    newWidth = originalImage.width/2
    frame1 = Image.new('RGB',(int(newWidth),originalImage.height))
    frame2 = Image.new('RGB',(int(newWidth),originalImage.height))

    frame1.paste(originalImage,(0,0))
    frame2.paste(originalImage,(int(-newWidth),0))

    frame1.save(destinationBasePath+'1'+extension)
    frame2.save(destinationBasePath+'2'+extension)
