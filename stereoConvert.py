from PIL import Image
import requests
from io import BytesIO
import pprint

def convertImage(imageUrl,imagePath):
    maxImageWidth = 2000
    print(f'fetching {imageUrl}')
    imageResponse = requests.get(imageUrl)
    imageBuffer = BytesIO(imageResponse.content)

    try:
        originalImage = Image.open(imageBuffer)
    except Image.UnidentifiedImageError as er:
        print('UnidentifiedImageError occurred: ' + imageUrl) #this keeps happening with imgur links TODO fix it
        return

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