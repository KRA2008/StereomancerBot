from PIL import Image
import requests
from io import BytesIO

def convertImage(imageUrl,imagePath):
    maxImageWidth = 2000
    imageResponse = requests.get(imageUrl)
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
    swappedImage.save(tempFileName)