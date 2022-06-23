import sys

import world_complexity
import os

def saveAsPGM(mapsPath):

    # convert all png to pgm
    for subdir, dirs, files in os.walk(mapsPath):
        for file in files:
            # print os.path.join(subdir, file)
            filepath = subdir + os.sep + file

            if filepath.endswith(".png"):
                pre, ext = os.path.splitext(filepath)
                os.rename(filepath, pre + '.pgm')

    # store all file paths of pgm, yaml and destinations
    filepathListPGM = []
    filepathListYAML = []

    for subdir, dirs, files in os.walk(mapsPath):
        for file in files:
            # print os.path.join(subdir, file)
            filepath = subdir + os.sep + file

            if filepath.endswith('.pgm'):
                filepathListPGM.append(filepath)
            elif filepath.endswith('.world.yaml'):
                print('ignore world.yaml: ' + filepath)
            elif file == 'complexity.yaml':
                print('ignore complexity.yaml: ' + filepath)
            elif filepath.endswith('.yaml'):
                filepathListYAML.append(filepath)

            print(filepath)

    return filepathListPGM, filepathListYAML

def write2File(filepath, mapdata):
    file = open(filepath, 'w')

    for element in mapdata:
        file.write(element)
        file.write('\n')
    file.close()


if __name__ == '__main__':

    mapsPath = '/home/valentin/AA/generated_maps'
    print(mapsPath)
    listPGM, listYAML = saveAsPGM(mapsPath)
    mapdata = []

    for i in range(0, len(listPGM)):
        print(os.path.dirname(listPGM[i]))
        data = world_complexity.main(listPGM[i], listYAML[i], os.path.dirname(listPGM[i]))
        mapdata.append(str(data))
    print('calculated values!')
    csvPath = mapsPath + '/map_worldcomplexity_results.csv'
    write2File(csvPath, mapdata)

    print('complexity results in: ' + csvPath)






