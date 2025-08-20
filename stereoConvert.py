from PIL import Image
import requests
from io import BytesIO
import pprint

def convertImage(imageUrl,imagePath,userAgent):
    maxImageWidth = 2000
    print(f'fetching {imageUrl}')
    headers = {
        'User-Agent':userAgent #required by imgur
    }
    imageResponse = requests.get(imageUrl,headers=headers)

    if imageResponse.status_code != 200:
        print('image fetching failed: ' + str(imageResponse.status_code))
        return

    originalImage = Image.open(BytesIO(imageResponse.content))


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