from PIL import Image
from io import BytesIO

async def convertImage(imageUrl,imagePath,userAgent,session):
    maxImageWidth = 2000
    print(f'fetching {imageUrl}')
    headers = {
        'User-Agent':userAgent #required by imgur
    }
    async with session.get(url=imageUrl,headers=headers) as response:
        responseResult = await response.read()
        if response.status != 200:
            print('image fetching failed: ' + str(response.status))
            return
        originalImage = Image.open(BytesIO(responseResult))

    if originalImage.width > maxImageWidth:
        originalImage = originalImage.resize((int(maxImageWidth),int(maxImageWidth * originalImage.height / originalImage.width)))
    
    swappedImage = Image.new(mode=originalImage.mode,size=originalImage.size)

    leftStart = (int(originalImage.width/-2),0)
    rightStart = (int(originalImage.width/2),0)
    swappedImage.paste(originalImage,leftStart)
    swappedImage.paste(originalImage,rightStart)

    if swappedImage.mode in ('RGBA','P'):
        swappedImage = swappedImage.convert('RGB')

    tempFileName=imagePath
    print(f'saving to {tempFileName}')
    swappedImage.save(tempFileName)