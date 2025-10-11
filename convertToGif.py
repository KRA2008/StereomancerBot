import stereoConvert
from PIL import Image
import subprocess
from difflib import SequenceMatcher


def printStringSimilarity(string1,string2):
    matchRatio = SequenceMatcher(None, string1, string2).ratio()
    print(str(len(string1)) + ' ' + str(matchRatio))


def main():
    print("")
    printStringSimilarity(""," (OC)")
    printStringSimilarity("x","graeerf")
    printStringSimilarity("Pills","teheaa4e4ter")
    printStringSimilarity("Somber Carpet Moth","Somber Carpet Moth (OC)")
    printStringSimilarity("Still life, glass and bowl and shadow","Still life, glass and bowl and shadow (OC)")
    printStringSimilarity("Photographer by day, Ren Faire pirate by weekend.","Photographer by day, Ren Faire pirate by weekend. (OC)")

main()