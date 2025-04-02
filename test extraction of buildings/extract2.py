import json
import numpy as np
import rasterio
from shapely.geometry import Polygon
from shapely.wkt import loads
from rasterio.transform import Affine
import os

def geo_to_pixel(lon, lat, affine_transform):
    x, y = ~affine_transform * (lon, lat)
    return x, y

def extract_building_from_image(image_path, json_path, output_dir, geotransform_json_path):
    with rasterio.open(image_path) as src:
        image_width = src.width
        image_height = src.height

        # Extract image name from path
        image_name = os.path.basename(image_path)

        # Load geotransform data from JSON
        with open(geotransform_json_path, 'r') as f:
            geotransform_data_dict = json.load(f)

        # Get geotransform data for the specific image
        geotransform_data = geotransform_data_dict.get(image_name)

        if geotransform_data is None:
            print(f"Error: Geotransform data not found for image {image_name}.")
            return

        # Create Affine transform from geotransform data
        gt = geotransform_data[0]
        affine_transform = Affine(gt[1], gt[2], gt[0], gt[4], gt[5], gt[3])

        print(f"Image dimensions: {image_width}x{image_height}")
        print(f"Affine transform: {affine_transform}")

        with open(json_path) as f:
            json_data = json.load(f)

        buildings = json_data['features']['lng_lat']

        # Create the main output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)

        for building in buildings:
            uid = building['properties']['uid']
            wkt_str = building['wkt']
            damage_type = building['properties']['subtype']

            polygon = loads(wkt_str)

            minx, miny, maxx, maxy = polygon.bounds

            x_min, y_min = geo_to_pixel(minx, maxy, affine_transform)
            x_max, y_max = geo_to_pixel(maxx, miny, affine_transform)

            x_min = max(0, int(x_min))
            y_min = max(0, int(y_min))
            x_max = min(image_width, int(x_max))
            y_max = min(image_height, int(y_max))

            building_image = src.read([1, 2, 3], window=((y_min, y_max), (x_min, x_max)))

            # Create the damage-specific subfolder if it doesn't exist
            damage_folder = os.path.join(output_dir, damage_type)
            os.makedirs(damage_folder, exist_ok=True)

            output_file = os.path.join(damage_folder, f"building_{uid}.png")
            with rasterio.open(output_file, 'w', driver='PNG', height=(y_max - y_min), width=(x_max - x_min),
                               count=3, dtype=building_image.dtype, crs=src.crs, transform=affine_transform) as out:
                out.write(building_image)
            print(f"Building {uid} image saved to {output_file}")

# Example Usage (replace with your actual paths)
image_path = 'mexico-earthquake_00000073_post_disaster.png'
json_path = 'mexico-earthquake_00000073_post_disaster.json'
output_dir = 'buildings'
geotransform_json_path = 'xview_geotransforms.json'  # Path to your geotransform JSON

extract_building_from_image(image_path, json_path, output_dir, geotransform_json_path)