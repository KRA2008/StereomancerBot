from PIL import Image

def convertToAnaglyph(filePath):
    with Image.open(filePath) as originalImage:
        leftMatrix = ( 0, 0, 0, 0,
                       0, 1, 0, 0,
                       0, 0, 1, 0)
        
        rightMatrix = ( 1, 0, 0, 0,
                        0, 0, 0, 0,
                        0, 0, 0, 0)
    
        newImageWidth = originalImage.width/2
        leftImage = Image.new('RGB',(int(newImageWidth),originalImage.height))
        rightImage = Image.new('RGB',(int(newImageWidth),originalImage.height))
        newImage = Image.new('RGBA',(int(newImageWidth),originalImage.height))

        leftImage.paste(originalImage,(0,0))
        leftImage = leftImage.convert('RGB',leftMatrix)
        #leftImage.show()

        rightImage.paste(originalImage,(int(-newImageWidth),0))
        rightImage = rightImage.convert('RGB',rightMatrix)
        #rightImage.show()

        #rightImage.putalpha(127)
        newImage.paste(rightImage,(0,0),rightImage)
        leftImage.putalpha(127)
        newImage.paste(leftImage,(0,0),leftImage)
        newImage.show()

convertToAnaglyph('temp/cross.JPG')