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

def extract_building_from_image(image_path, json_path, output_dir, geotransform_json_path, image_type):
    with rasterio.open(image_path) as src:
        image_width = src.width
        image_height = src.height

        image_name = os.path.basename(image_path)

        with open(geotransform_json_path, 'r') as f:
            geotransform_data_dict = json.load(f)

        geotransform_data = geotransform_data_dict.get(image_name)

        if geotransform_data is None:
            print(f"Error: Geotransform data not found for image {image_name}.")
            return

        gt = geotransform_data[0]
        affine_transform = Affine(gt[1], gt[2], gt[0], gt[4], gt[5], gt[3])

        print(f"Image dimensions: {image_width}x{image_height}")
        print(f"Affine transform: {affine_transform}")

        with open(json_path) as f:
            json_data = json.load(f)

        buildings = json_data['features']['lng_lat']

       
        image_type_folder = os.path.join(output_dir, image_type)
        os.makedirs(image_type_folder, exist_ok=True)

        for building_index, building in enumerate(buildings):
            wkt_str = building['wkt']

            polygon = loads(wkt_str)

            minx, miny, maxx, maxy = polygon.bounds

            x_min, y_min = geo_to_pixel(minx, maxy, affine_transform)
            x_max, y_max = geo_to_pixel(maxx, miny, affine_transform)

            x_min = max(0, int(x_min))
            y_min = max(0, int(y_min))
            x_max = min(image_width, int(x_max))
            y_max = min(image_height, int(y_max))

            building_image = src.read([1, 2, 3], window=((y_min, y_max), (x_min, x_max)))

            # Save buildings with index as filename(pre)
            if image_type == "pre-disaster":
                output_file = os.path.join(image_type_folder, f"building_{building_index + 1}.png")
            else:  # For post-disaster
                damage_type = building['properties']['subtype']
                damage_folder = os.path.join(image_type_folder, damage_type)
                os.makedirs(damage_folder, exist_ok=True)
                output_file = os.path.join(damage_folder, f"building_{building_index + 1}_{damage_type}.png")

            with rasterio.open(output_file, 'w', driver='PNG', height=(y_max - y_min), width=(x_max - x_min),
                               count=3, dtype=building_image.dtype, crs=src.crs, transform=affine_transform) as out:
                out.write(building_image)
            print(f"Building {building_index + 1} image saved to {output_file}")

            # Delete the XML files
            xml_file = output_file + ".aux.xml"
            if os.path.exists(xml_file):
                os.remove(xml_file)


pre_disaster_image_path = 'mexico-earthquake_00000073_pre_disaster.png'
pre_disaster_json_path = 'mexico-earthquake_00000073_pre_disaster.json'
post_disaster_image_path = 'mexico-earthquake_00000073_post_disaster.png'
post_disaster_json_path = 'mexico-earthquake_00000073_post_disaster.json'
output_dir = 'buildings'
geotransform_json_path = 'xview_geotransforms.json'

extract_building_from_image(pre_disaster_image_path, pre_disaster_json_path, output_dir, geotransform_json_path, "pre-disaster")
extract_building_from_image(post_disaster_image_path, post_disaster_json_path, output_dir, geotransform_json_path, "post-disaster")