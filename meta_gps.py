import base64
from io import BytesIO

from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
import folium
from folium import IFrame

import os
from tkinter import filedialog

from folium.plugins import HeatMap


# 지도에 마킹할 이미지가 있는 폴더 선택(모바일사용에선 제외될 수도)
def select_folder():
    try:
        dir_path = filedialog.askdirectory(initialdir=r"C:\Users\user\Desktop", title="폴더를 선택 해 주세요")

        if not dir_path:
            print("폴더가 선택되지 않았습니다.")
            return None

        # 폴더에 있는 이미지 파일 리스트 넣기
        res = [file for file in os.listdir(dir_path) if file.lower().endswith(('.png', '.jpg', '.jpeg'))]

        if len(res) == 0:
            print("폴더내 이미지 파일이 없습니다.")
        else:
            print(f"total:{len(res)}")
            print(res)  # folder 내 파일 목록 값 출력

        image_paths = [f"{dir_path}/{file}" for file in res]
        print(image_paths)

        return image_paths

    except Exception as e:
        print(e)
        pass

# 이미지의 gpsInfo 추출
def get_gps_info(image_file_path):
    try:
        image = Image.open(image_file_path)
        exif_data = image._getexif()
        if exif_data:
            gps_info = {}
            for tag, value in exif_data.items():
                tag_name = TAGS.get(tag, tag)
                if tag_name == 'GPSInfo':
                    gps_data = {}
                    for gps_tag in value:
                        gps_tag_name = GPSTAGS.get(gps_tag, gps_tag)
                        gps_data[gps_tag_name] = value[gps_tag]
                    gps_info[tag_name] = gps_data
            return gps_info
        else:
            print("No EXIF data found in the image.")
            return None
    except Exception as e:
        print(f"Error: {e}")
        return None

# gpsInfo->위도,경도로 변환
def convert_gps(gps_info):
    try:
        if 'GPSInfo' in gps_info:
            gps_data = gps_info['GPSInfo']
            if ('GPSLatitude' in gps_data and 'GPSLongitude' in gps_data and
                    'GPSLatitudeRef' in gps_data and 'GPSLongitudeRef' in gps_data):

                gps_latitude = gps_data['GPSLatitude']
                gps_longitude = gps_data['GPSLongitude']
                gps_latitude_ref = gps_data['GPSLatitudeRef']
                gps_longitude_ref = gps_data['GPSLongitudeRef']

                # Calculate latitude
                lat_degrees = gps_latitude[0]
                lat_minutes = gps_latitude[1]
                lat_seconds = gps_latitude[2]
                latitude = lat_degrees + (lat_minutes / 60.0) + (lat_seconds / 3600.0)
                if gps_latitude_ref == 'S':
                    latitude = -latitude

                # Calculate longitude
                lon_degrees = gps_longitude[0]
                lon_minutes = gps_longitude[1]
                lon_seconds = gps_longitude[2]
                longitude = lon_degrees + (lon_minutes / 60.0) + (lon_seconds / 3600.0)
                if gps_longitude_ref == 'W':
                    longitude = -longitude

                return latitude, longitude
            else:
                print("Error: GPS latitude or longitude information is missing.")
                return None
        else:
            print("Error: GPSInfo key not found in gps_info.")
            return None
    except Exception as e:
        print(f"Error in convert_gps function: {e}")
        return None

def correct_image(image_path):
    img = Image.open(image_path)
    try:
        exif = img._getexif()
        for tag, value in exif.items():
            if TAGS.get(tag) == 'Orientation':
                if value == 3:
                    img = img.rotate(180, expand=True)
                elif value == 6:
                    img = img.rotate(270, expand=True)
                elif value == 8:
                    img = img.rotate(90, expand=True)
                break
    except (AttributeError, KeyError, IndexError):
        pass

    return img
def get_datetime_original(image_file_path):
    image = Image.open(image_file_path)
    exif_data = image._getexif()
    if exif_data:
        # for tag, value in exif_data.items():
        #     if TAGS.get(tag) == 'DateTimeOriginal':
        #         return value
        return next((value for tag,value in exif_data.items() if TAGS.get(tag)=='DateTimeOriginal'),None)
    return None
# 이미지 팝업 생성
def create_popup(image_path):
    img = correct_image(image_path)
    img = img.resize((300, 300), Image.LANCZOS) #리사이즈 안하면 이미지출력 안됨

    photo_date = get_datetime_original(image_path)
    buffered = BytesIO()
    img.save(buffered, format="JPEG")
    img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')

    html = '<img src="data:image/jpg;base64,'+ img_base64 + f'" width="300px"><h5>파일명 : {image_path.split("/")[-1]}</h5><h5>사진생성시간 : {photo_date}</h5>'
    iframe = IFrame(html, width=310, height=420)
    return folium.Popup(iframe)

def markOnMap(image_path, map_folium, heat_data):
    gps_info = get_gps_info(image_path)
    if not gps_info:
        print(f"No GPS info found for {image_path}")
        return

    exif_gps = convert_gps(gps_info)
    if not exif_gps:
        print(f"Error converting GPS for {image_path}")
        return

    print(image_path)
    popup = create_popup(image_path)
    if not popup:
        print(f"Error creating popup for {image_path}")
        return

    heat_data.append(exif_gps)
    tool_tip = image_path.split('/')    # 이미지 파일명만 표시
    folium.Marker(exif_gps, popup=popup, tooltip=tool_tip[-1]).add_to(map_folium)


if __name__ == "__main__":
    image_paths = select_folder()
    if image_paths:
        map_center = [36.3, 128]
        # folium.Map(location=[위도, 경도], zoom_start=지도 배율)
        map_folium = folium.Map(location=map_center, zoom_start=8)

        heat_data = []
        for path in image_paths:
            gps_info = get_gps_info(path)
            if gps_info:
                print("GPS Info:")
                print(gps_info)

                markOnMap(path, map_folium, heat_data)

        if heat_data:
            HeatMap(heat_data).add_to(map_folium)

        map_folium.save('my_map.html')

