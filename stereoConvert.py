from PIL import Image
from io import BytesIO


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

    swappedImage.save(imagePath)
    print(f'saved {imagePath}')


async def convertSbsToAnaglyph(imageUrl,imagePath,userAgent,session,isCross):
    originalImage = await downloadAndDownsizeImage(imageUrl,userAgent,session)
    
    newImageWidth = originalImage.width/2
    image1 = Image.new('RGB',(int(newImageWidth),originalImage.height))
    image2 = Image.new('RGB',(int(newImageWidth),originalImage.height))

    image1.paste(originalImage,(0,0))
    r1,g1,b1 = image1.split()

    image2.paste(originalImage,(int(-newImageWidth),0))
    r2,g2,b2 = image2.split()

    if isCross:
        newImage = Image.merge('RGB',(r2,g1,b1))
    else:
        newImage = Image.merge('RGB',(r1,g2,b2))

    newImage.save(imagePath)
    print(f'saved {imagePath}')