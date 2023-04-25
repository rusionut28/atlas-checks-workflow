"""
Run Atlas checks on a country against .pbf files
@author: Ionut Rus
@history: 14/04/2023 Created

"""


import os
import json
from collections import defaultdict
import requests
import subprocess

"""

Download country subdivisions from
https://github.com/stephanietuerk/admin-boundaries/tree/master/lo-res/Admin2_simp05
Split into separate geojson file for each subdivision

"""


# URL of the GeoJSON file
url = 'https://raw.githubusercontent.com/stephanietuerk/admin-boundaries/master/lo-res/Admin1_simp10/gadm36_PHL_1.json'

# Send a GET request to the website to download the file
response = requests.get(url)

# Write the file to disk
with open('gadm36_PHL_1.json', 'wb') as f:
    f.write(response.content)

# Path to the input GeoJSON file
input_file = 'gadm36_PHL_1.json'

# Path to the output directory
output_dir = 'subdivisions_PHL'

# Create the output directory if it doesn't exist
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

# Load the input GeoJSON file
with open(input_file) as f:
    data = json.load(f)

# Loop over the features and split the GeoJSON into subdivisions using ogr2ogr
for feature in data['features']:
    name = feature['properties']['NAME_1']
    filename = os.path.join(output_dir, f'{name.replace(" ", "_")}.geojson')
    subprocess.run(['ogr2ogr', '-f', 'GeoJSON', '-lco', 'COORDINATE_PRECISION=5', '-nln', 'subdivision', '-skipfailures', '-where', f"NAME_1 = '{name}'", filename, input_file])



def extract_pbf_files(input_dir):
    """
    Extracts PBF files using osmium from all geojson files in the specified input directory.

    :param input_dir: Path to directory containing input subdivisions geojson files.
    :return: List of paths to extracted PBF files.
    """
    pbf_files = []
    for file in os.listdir(input_dir):
        if file.endswith(".geojson"):
            filename = os.path.splitext(file)[0]
            pbf_filename = f"{filename}.pbf"
            os.system(f"osmium extract -p {os.path.join(input_dir, filename)}.geojson philippines-latest.osm.pbf -o {pbf_filename}")
            pbf_files.append(pbf_filename)
    return pbf_files


def process_pbf_files(pbf_files):
    """
    Processes PBF files using Gradle.

    :param pbf_files: List of paths to PBF files.
    """
    for file in pbf_files:
        folder_name = os.path.splitext(file)[0]
        os.mkdir(folder_name)
        os.system(f"./gradlew run -Pchecks.local.sharded=false -Pchecks.local.input={file} -Pchecks.local.output=file://{os.getcwd()}/{folder_name}/output/ > {folder_name}/output.txt")


def merge_geojson_files(input_dir_result, output_dir):
    """
    Merges GeoJSON files from the specified input directory into a single file in the specified output directory.

    :param input_dir_result: Path to directory containing the resulting geojson files.
    :param output_dir: Path to output directory.
    """
    
    
    print("Merging GeoJSON files...")
    feature_collections = defaultdict(list)
    for root, dirs, files in os.walk(input_dir_result):
        for file in files:
            if file.endswith(".geojson"):
                filename = os.path.splitext(file)[0]
                name = filename.split("-", 1)[0]
                with open(os.path.join(root, file), "r") as f:
                    geojson = json.load(f)
                    feature_collections[name].append(geojson["features"])

    for name, features in feature_collections.items():
        output_file = os.path.join(output_dir, name + ".geojson")
        feature_collection = {
            "type": "FeatureCollection",
            "features": []
        }
        for feature_list in features:
            feature_collection["features"].extend(feature_list)
        with open(output_file, "w") as f:
            json.dump(feature_collection, f)


input_dir = input("Enter the input folder containing the subdivisions GeoJSON files: ")
pbf_files = extract_pbf_files(input_dir)
process_pbf_files(pbf_files)

input_dir_result = input("Enter the folder path containing the resulting GeoJSON files: ")
output_dir = input("Enter the output folder path for merged GeoJSON files: ")
merge_geojson_files(input_dir_result, output_dir)

print("Done!")
