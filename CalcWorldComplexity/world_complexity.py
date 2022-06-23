import math
import cv2
import sys
import yaml
import os
import rospkg
import numpy as np
from argparse import ArgumentParser
from collections import Counter
from scipy import spatial
from pathlib import Path
from matplotlib import pyplot as plt
from collections import namedtuple
from unittest import skip

# TODO s
# - die angle liste soll man trennen, weil gerade in einer liste gespeichert werden und ich weiß nicht, welche in welche

# see comments at the end of the document

ROBOT_RADIUS = 0.3  # [m]
MIN_INTENDED_WALKWAY_WITH = 0.2  # [m]
# [m]: the obs must be at least 20 cm to avoid detecting obstacles that are not actually there due to miscoloured pixel
MIN_OBS_SIZE = 0.2


class Complexity:

    def __init__(self):
        self.density_gird = []

    def extract_data(self, img_path: str, yaml_path: str):

        # reading in the image and converting to 0 = occupied, 1 = not occupied
        if img_path[-3:] == 'pgm' or img_path[-3:] == 'jpg':
            img_origin = cv2.imread(img_path)
            img = cv2.cvtColor(img_origin, cv2.COLOR_BGR2GRAY)
            # convert image pixels to binary pixels 0 or 255
            th, dst = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY)

        # for infos on parameters: http://wiki.ros.org/map_server
        with open(yaml_path, 'r') as stream:
            map_info = yaml.safe_load(stream)

        # this only selects interior area
        t = np.where(img == 0.0)
        x_low_lim = min(t[0])
        x_high_lim = max(t[0])
        y_low_lim = min(t[1])
        y_high_lim = max(t[1])
        print(x_low_lim, x_high_lim)
        test = img[x_low_lim:x_high_lim, y_low_lim:y_high_lim]
        # cv2.imshow('test',test)
        # cv2.waitKey(0)
        return img_origin, img, map_info

    def determine_map_size(self, img: list, map_info: dict):
        """Determining the image size by using resolution in meters
        """
        return map_info['resolution'] * img.shape[0] * img.shape[1]

    def occupancy_ratio(self, img: list):
        """Proportion of the occupied area
        """
        # TODO to find the actual occupancy only interior occupied pixels should be taken into account
        # idea get the pos on the sides (a,b,c,d) where the value is first 0, use: https://stackoverflow.com/questions/9553638/find-the-index-of-an-item-in-a-list-of-lists
        free_space = np.count_nonzero(img)
        return 1 - free_space / (img.shape[0] * img.shape[1])

    def occupancy_distribution(self, img: list):
        # Idea: https://jamboard.google.com/d/1ImC7CSPc6Z3Dkxh5I1wX_kkTjEd6GFWmMywHR3LD_XE/viewer?f=0
        raise NotImplementedError

    def entropy(self, img_gray):
        """ Measures the amount of disorder of in the image (between the obstacles). Proposed here: Performance Measure For The Evaluation of Mobile Robot Autonomy
        """
        features = []
        th, dst = cv2.threshold(img_gray, 0, 255, cv2.THRESH_BINARY)
        windows = self.sliding_window(dst, 2, (2, 2))
        windowList = []
        for window in windows:
            windowList.append(window)
            featureVector = self.extractFeatures(window)
        pList = []
        count = Counter(featureVector)
        p_zero = count[0.0] / len(featureVector)
        p_one = count[1] / len(featureVector)
        p_two = count[0.25] / len(featureVector)
        p_five = count[0.5] / len(featureVector)
        p_seven = count[0.75] / len(featureVector)
        pList.append(p_zero)
        pList.append(p_one)
        pList.append(p_two)
        pList.append(p_five)
        pList.append(p_seven)
        entropy = 0
        for pDensity in pList:
            if pDensity != 0:
                entropy += (pDensity) * np.log(pDensity)
        entropy = (-1) * entropy
        maxEntropy = np.log2(5)
        print('calculated entropy:', entropy)
        print('Max. Entropy:', maxEntropy)
        return float(entropy), float(maxEntropy)

    def sliding_window(self, image, stepSize, windowSize):
        for y in range(0, image.shape[0], stepSize):
            for x in range(0, image.shape[1], stepSize):
                yield (x, y, image[y:y + windowSize[1], x:x + windowSize[0]])

    def extractFeatures(self, window):

        freq_obstacles = window[2] == 0
        total = freq_obstacles.sum()
        density = total * 1 / 4
        self.density_gird.append(density)

        return self.density_gird

    def check_surrounding(self, img, i, j, obs_coordinates):
        """Determining all pixels that are occupied by this obstacle
        args:
            img: the floor plan
            i,j: start coordinate of the obstacle
            obs_coordinates: list of coordinates occupied by this obstacle

        return:
            img: floor plan without the obstacle on it
            obs_coordinates: tuple of all pixel-indices occupied by the obstacle
        """

        # marking the pixel and setting it to not occupied to avoid double assignment
        obs_coordinates.append((i, j))
        img[i, j] = 205

        # for every point we check in a star pattern, whether the surrounding cells are occupied also
        if i+1 < img.shape[0]:
            if j+1 < img.shape[1]:

                if img[i-1][j] == 0 and i >= 1:
                    self.check_surrounding(img, i-1, j, obs_coordinates)
                if img[i+1][j] == 0 and i+1 <= img.shape[0]:
                    self.check_surrounding(img, i+1, j, obs_coordinates)
                if img[i][j-1] == 0 and j >= 1:
                    self.check_surrounding(img, i, j-1, obs_coordinates)
                if img[i][j+1] == 0 and i+1 <= img.shape[1]:
                    self.check_surrounding(img, i, j+1, obs_coordinates)

        return img, obs_coordinates

    def number_of_static_obs(self, img: list, map_info):
        """Determining the obstacle in the image incl. their respective pixels
        args:
            img: floorplan to evaluate
        """
        # to allow more recursive function calls
        sys.setrecursionlimit(20000)

        global obs_list
        obs_list = {}
        obs_num = 0

        # number of pixels an obstacle must have at least (default = 2)
        min_pix_size = MIN_OBS_SIZE / map_info['resolution']

        # going through every pixel and checking if its occupied
        for pixel_y in range(img.shape[1]):
            for pixel_x in range(img.shape[0]):
                if img[pixel_x, pixel_y] == 0:
                    obs_coordinates = []
                    img, temp = self.check_surrounding(
                        img, pixel_x, pixel_y, obs_coordinates)
                    if len(temp) >= min_pix_size:
                        obs_list[obs_num] = temp
                        obs_num += 1

        return len(obs_list)

    def distance_between_obs(self, map_info):
        """Finds distance to all other obstacles
        """
        def do_kdtree(combined_x_y_arrays, points):
            mytree = spatial.cKDTree(combined_x_y_arrays)
            dist, _ = mytree.query(points)
            return dist

        # the walkway should be at least this whide to be considert has walkway
        min_walkway_size = MIN_INTENDED_WALKWAY_WITH / map_info['resolution']

        min_obs_dist = 10000  # large number
        for key, coordinates in obs_list.items():

            distances = []
            for key_other, coordinates_other in obs_list.items():
                if key_other == key:
                    continue
                # this checks the distance between the pixels of the obstacles, and only selects the min distance between the pixels
                dist_between_pixel_arrays = do_kdtree(
                    np.array(coordinates_other), np.array(coordinates))
                filtered_pix = dist_between_pixel_arrays[dist_between_pixel_arrays >
                                                         min_walkway_size]
                if len(filtered_pix) > 0:
                    min_dist_between_pixel_arrays = min(filtered_pix)
                if min_obs_dist > min_dist_between_pixel_arrays:
                    min_obs_dist = min_dist_between_pixel_arrays

        print(min_obs_dist)

        return float(min_obs_dist * map_info['resolution'])

    def no_obstacles(self, path, list_of_all_angles):
        """ finds all obstacles and determines there center
        """
        areaList = []
        xcoordinate_center = []
        ycoordinate_center = []
        image = cv2.imread(path)
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        (thresh, blackAndWhiteImage) = cv2.threshold(gray, 127, 255,
                                                     cv2.THRESH_BINARY)
        blur = cv2.GaussianBlur(gray, (11, 11), 0)
        canny = cv2.Canny(blur, 30, 40, 3)
        dilated = cv2.dilate(canny, (5, 5), iterations=0)

        (cnt, hierarchy) = cv2.findContours(
            dilated.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        cv2.drawContours(rgb, cnt, -1, (0, 255, 0), 2)
        # cv2.imshow('map5', rgb)
        print("No of circles: ", len(cnt))
        for c in cnt:
            if cv2.contourArea(c) > 1:
                area = int(cv2.contourArea(c))
                areaList.append(area)
                length = int(cv2.arcLength(c, True))
                M = cv2.moments(c)
                xcoord = int(M['m10'] / M['m00'])
                ycoord = int(M['m01'] / M['m00'])
                xcoordinate_center.append(xcoord)
                ycoordinate_center.append(ycoord)
                coordList = [area, length, xcoord, ycoord]
        self.world_angles(xcoordinate_center, ycoordinate_center, list_of_all_angles)

        # fig=plt.figure()
        # ax=fig.add_subplot(1, 1, 1)
        # ax.xaxis.set_ticks_position('top')
        # ax.yaxis.grid(linestyle = '-', color = 'gray')
        # ax.invert_yaxis()
        # ax.plot(xcoordinate_center, ycoordinate_center, 'ro', linewidth = 1.5)
        # # V this adds the lines V
        # for x, y in zip(xcoordinate_center, ycoordinate_center):
        #     plt.plot([0, x], [0, y], color = "blue")
        #     # ^ this adds the lines ^
        #     plt.plot(x, y, 0, 0, linestyle = '--')

        # plt.show()
        cv2.waitKey(10000)
        print(
            f'OBS nr: {len(xcoordinate_center)} \n xcoordinate_center {xcoordinate_center} \n ycoordinate_center: {ycoordinate_center}')
        return xcoordinate_center, ycoordinate_center

    def world_angles(self, xCoord: list, yCoord: list, list_of_all_angles):
        """ calculates the angels between the obstacles in each window
        args:
            xCoord: x-coordinate of the center of each obs
            yCoord: y-coordinate of the center of each obs
        """

        xIndices = []
        xIndices_interval = []
        intervalPointList = []
        angle = []
        subAngleList = []

        xInterval = [min(xCoord) - 10,
                     min(xCoord) + 10]  # finds the smallest x_coordination and forms an interval with +-10
        # print('xInterval', xInterval)
        # find the index of this point to find the corresponding y_coordinate
        for (index, item) in enumerate(xCoord):
            if item == min(xCoord):
                xIndices.append(index)

        xMax = max(xCoord)
        yMin = min(yCoord)
        yMax = max(yCoord)
        # print(yMax)
        # print(xCoord)
        # print(yCoord)

        # because we want the point with smallest x and y, we should check if y is also the smallest
        if yCoord[xIndices[
                0]] - 10 > yMin:
            yInterval = [yMin - 1, yCoord[xIndices[0]] + 10]
        else:
            yInterval = [yCoord[xIndices[0]] - 10, yCoord[xIndices[0]] + 10]

        orgYInterval = yInterval
        listLength = len(xCoord)
        counter = 0

        # loop interval in y direction
        while yInterval[1] <= yMax + 10 and xInterval[1] <= xMax + 10:
            for (index, item) in enumerate((xCoord)):  # we find all points that are in this interval
                counter += 1

                # find x and indices of x in interval
                if item <= xInterval[1] and item >= xInterval[0]:
                    xIndices_interval.append(index)
                    # find y with indices of x
                    if yCoord[index] <= yInterval[1] and yCoord[index] >= yInterval[0]:
                        # find coordination of point in interval
                        intervalPointList.append([item, yCoord[index]])
                        point = [item, yCoord[index]]
                        xCenter = (xInterval[1] - xInterval[0])/2
                        yCenter = (yInterval[1] - yInterval[0]) / 2
                        # calculate angle of all points in interval to the first x,y of interval
                        angle.append(self.get_angle(
                            [xInterval[0] + xCenter, yInterval[0] + yCenter], point))
                      #  angle.append(self.get_angle([xInterval[0] + xCenter, yInterval[0] + yCenter], point))
                        # print('point', point)
                        # print('x interval', xInterval)
                        # print('y Interval', yInterval)
                        # print('center of Interval, ', [
                        #   xInterval[0] + xCenter, yInterval[0] + yCenter])
                        # print('angles to x-axis', angle)

                if listLength == counter:  # when the y interval is over, window should go in x direction and then again in y direction, to find the new points
                    yInterval = [yInterval[1], yInterval[1]+10]
                    sortedAngle = sorted(angle)
                    for index in range(len(sortedAngle)):
                        if index != 0:
                            sub = sortedAngle[index] - sortedAngle[index-1]
                            subAngleList.append(sub)
                    sumAngles = sum(subAngleList)
                    lastAngle = 360 - sumAngles
                    subAngleList.append(lastAngle)
                    # print('angles between every obstacle', subAngleList)
                    #global list_of_all_angles
                    # list_of_all_angles.append([len(subAngleList)])
                    list_of_all_angles.append(subAngleList)
                    subAngleList = []
                    angle = []
                    counter = 0

            if not (yInterval[1] <= yMax + 10):
                xInterval = [xInterval[1], xInterval[1] + 10]
                yInterval = orgYInterval

    Point = namedtuple("Point", ["x", "y"])

    def get_angle(self, p1: Point, p2: Point) -> float:
        """Get the angle of this line with the horizontal axis."""

        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        theta = math.atan2(dy, dx)
        angle = math.degrees(theta)  # angle is in (-180, 180]
        if angle < 0:
            angle = 360 + angle

        return angle

    def processing_angle_information(self, list_of_all_angles):
        """Evaluates the angle information of the obstacles, by taking in a list of all angles as input
        """
        #global list_of_all_angles
        angle_data = {}
        nr_windows = len(list_of_all_angles)
        list_of_all_angles = [
            item for sublist in list_of_all_angles for item in sublist]  # flatten the list
        angle_data['mean'] = float(np.mean(list_of_all_angles))
        angle_data['variance'] = float(np.var(list_of_all_angles))
        if 0 not in [angle_data['mean'], angle_data['variance']]:
            angle_data['adjusted_mean'] = float(
                angle_data['mean'] / angle_data['variance'])

        return angle_data

    def save_information(self, data: dict, dest: str):
        """To save the evaluated metrics
        args:
            data: data of the evaluated metrics
            dest: path were the data should be saved
        """
        os.chdir(dest)
        with open(f'complexity.yaml', 'w+') as outfile:
            yaml.dump(data, outfile, default_flow_style=False)


def main(imagePath, yamlPath, destPath):
    #dir = rospkg.RosPack().get_path('arena-tools')

    # reading in user data
    parser = ArgumentParser()
    parser.add_argument("--image_path", action="store", dest="image_path",
                        default=f"/home/elias/catkin_ws/src/arena-rosnav-3D/simulator_setup/maps/ignc/map.pgm",
                        help="path to the floor plan of your world. Usually in .pgm format",
                        required=False)
    parser.add_argument("--yaml_path", action="store", dest="yaml_path",
                        default=f"/home/elias/catkin_ws/src/arena-rosnav-3D/simulator_setup/maps/ignc/map.yaml",
                        help="path to the .yaml description file of your floor plan",
                        required=False)
    parser.add_argument("--dest_path", action="store", dest="dest_path",
                        help="location to store the complexity data about your map",
                        required=False)
    args = parser.parse_args()
    converted_dict = vars(args)
    file_name = Path(converted_dict['image_path']).stem

    # extract data
    img_origin, img, map_info = Complexity().extract_data(
        imagePath, yamlPath)

    data = {}
    list_of_all_angles = []
    Complexity().no_obstacles(imagePath, list_of_all_angles)

    # calculating metrics
    data["Entropy"], data["MaxEntropy"] = Complexity().entropy(img)
    data['MapSize'] = Complexity().determine_map_size(img, map_info)
    data["OccupancyRatio"] = Complexity().occupancy_ratio(img)
    data["NumObs"] = Complexity().number_of_static_obs(img, map_info)
    data["MinObsDis"] = Complexity().distance_between_obs(map_info)
    data["AngleInfo"] = Complexity().processing_angle_information(list_of_all_angles)

    # dump results
    Complexity().save_information(data, destPath)

    print(data)

    return data


if __name__ == '__main__':

    imagePath = sys.argv[1]
    yamlPath = sys.argv[2]
    destPath = sys.argv[3]

    data = main(imagePath, yamlPath, destPath)


# NOTE: for our complexity measure we make some assumptions
# 1. We ignore the occupancy threshold. Every pixel > 0 is considert to be fully populated even though this is not entirely accurate since might also only partially be populated (we therefore slightly overestimate populacy.)
# 2. We assume the map shows only areas relevant for robot navigation (interior areas). For example having a large exterior area on your map, could lead do biased occupancy-ratio measurements
