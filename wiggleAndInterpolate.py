import stereoConvert
import numpy as np
import cv2 as cv
from PIL import Image
from typing import List, Tuple


def wiggleAndInterpolate():
    originalImage = Image.open('temp/flower.jpeg')

    wigglegramWidth = originalImage.width/2
    frame1 = Image.new('RGB',(int(wigglegramWidth),originalImage.height))
    frame2 = Image.new('RGB',(int(wigglegramWidth),originalImage.height))

    frame1.paste(originalImage,(0,0))
    frame2.paste(originalImage,(int(-wigglegramWidth),0))

    array1 = np.array(frame1)
    array2 = np.array(frame2)

    flow = calculate_optical_flow_between_frames(array1,array2)

    import cv2
    h, w = flow.shape[:2]
    flow = -flow
    flow[:,:,0] += np.arange(w)
    flow[:,:,1] += np.arange(h)[:,np.newaxis]
    midFrame = cv2.remap(array1, flow, None, cv.INTER_LINEAR)   

    frame1.save('temp/flower'+'.gif', save_all=True, append_images=[Image.fromarray(midFrame),frame2], duration=250, loop=0)


def calculate_optical_flow_between_frames(frame_1: np.ndarray, frame_2: np.ndarray) -> np.ndarray:
    frame_1_gray, frame_2_gray = cv.cvtColor(frame_1, cv.COLOR_BGR2GRAY), cv.cvtColor(frame_2, cv.COLOR_BGR2GRAY)
    optical_flow = cv.calcOpticalFlowFarneback(frame_1_gray,
                                                frame_2_gray,
                                                None,
                                                pyr_scale = 0.5,
                                                levels = 3,
                                                winsize = 10,
                                                iterations = 3,
                                                poly_n = 5,
                                                poly_sigma = 1.1,
                                                flags = 0
                                                )
    return optical_flow


wiggleAndInterpolate()