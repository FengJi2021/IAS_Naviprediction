import numpy as np
import cv2
from matplotlib import pyplot as plt
from skimage.restoration import denoise_tv_chambolle
import glob
import os
import itertools


path = "/home/nilou/Schreibtisch/geno/research/222702_planets/image2/*.png"
inputs = glob.glob(path)


class Filter:
    def filterImages(self, input, output):

        for image in inputs:
            fileBase = os.path.basename(image)
            noisy_image = cv2.imread(image)
            noisy_image = cv2.fastNlMeansDenoising(noisy_image, None, 80, 9, 21)
            image = cv2.cvtColor(noisy_image, cv2.COLOR_BGR2GRAY)
            se = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 40))
            bg = cv2.morphologyEx(image, cv2.MORPH_DILATE, se)
            out_gray = cv2.divide(image, bg, scale=255)
            out_binary = cv2.threshold(out_gray, 0, 255, cv2.THRESH_OTSU)[1]
            if not output == None:
                output_path = os.path.join(output, fileBase)
                cv2.imwrite(output_path, out_binary)
                print(fileBase)
                print(
                    "----------------------------------------------------------------------------------"
                )
            else:
                path = os.path.join(input, "/output")
                output_path = os.mkdir(path)
                cv2.imwrite(output_path, out_binary)
                print(fileBase)
                print(
                    "----------------------------------------------------------------------------------"
                )


def main():

    parser = Gooey(ArgumentParser())
    parser.add_argument(
        "--image_path",
        action="store",
        dest="image_path",
        help="path to the floor plan of your world. (in .pgm , .jpg or .png format)",
        required=True,
    )

    parser.add_argument(
        "--output_path",
        action="store",
        dest="output_path",
        help="output path where the generated images should be stored.",
        required=False,
    )

    args = parser.parse_args()
    Filter().filterImages(args.image_path, args.output_path)

if __name__ == "__main__":
    main()
