import os
import pandas as pd
import streamlit as st
import time
import json
import sys
import torch
import numpy as np
import faiss
from torchvision.models import resnet152, ResNet152_Weights
from torchvision.transforms import Compose, Resize, ToTensor, Normalize
import imageProcessing
import immich
from utility import display_asset_column, display_asset_info
from immich import get_asset_info
from streamlit_image_comparison import image_comparison
from datetime import datetime, timezone
import logging
logger = logging.getLogger(__name__)

# Set the environment variable to allow multiple OpenMP libraries
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

# Load ResNet152 with pretrained weights
model = resnet152(weights=ResNet152_Weights.DEFAULT)
model.eval()  # Set model to evaluation mode

def convert_image_to_rgb(image):
    """Convert image to RGB if it's RGBA."""
    if image.mode == 'RGBA':
        return image.convert('RGB')
    return image

transform = Compose([
    convert_image_to_rgb,
    Resize((224, 224)),  # Standard size for ImageNet-trained models
    ToTensor(),
    Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])

# Global variables for paths
index_path = 'faiss_index.bin'
metadata_path = 'metadata.npy'

def selected_metadata(assets):
    best_image_infos = None
    asset_infos = []
    # Fetch asset information and select the one with the largest resolution or if equal the largest image size
    for asset in assets:
        asset_id = asset['id']
        asset_info = immich.get_asset_info(asset_id)
        asset_infos.append(asset_info)
        if best_image_infos is None:
            best_image_infos = asset_info
        else:
            best_image_resolution = best_image_infos['exifInfo']['exifImageWidth'] * best_image_infos['exifInfo']['exifImageHeight']
            image_resolution = asset_info['exifInfo']['exifImageWidth'] * asset_info['exifInfo']['exifImageHeight']
            # Prefer larger resolution
            if image_resolution > best_image_resolution:
                best_image_infos = asset_info
            # If equal resolution, prefer the one with the larger file size
            elif image_resolution == best_image_resolution:
                if asset_info['exifInfo']['fileSizeInByte'] > best_image_infos['exifInfo']['fileSizeInByte']:
                    best_image_infos = asset_info
    # Select best image to keep
    st.session_state['keepImageId'] = best_image_infos['id']
    # If any asset is marked as favorite, set favorite
    st.session_state['isFavorite'] = any(info['isFavorite'] for info in asset_infos)
    # Prefere oldest dateTimeOriginal
    parsed_date_time_original = [datetime.fromisoformat(info['exifInfo']['dateTimeOriginal']) for info in asset_infos]
    st.session_state["dateTimeOriginal"] = min(parsed_date_time_original).astimezone(timezone.utc).isoformat(timespec='milliseconds')
    # Append all descriptions
    st.session_state["description"] = ''.join(info['exifInfo']['description'] for info in asset_infos)
    # Use any location... User has to confirm it.
    latitudes = [info['exifInfo']['latitude'] for info in asset_infos if info['exifInfo']['latitude'] is not None]
    longitudes = [info['exifInfo']['longitude'] for info in asset_infos if info['exifInfo']['longitude'] is not None]
    st.session_state["latitude"] = latitudes[0] if latitudes else None
    st.session_state["longitude"] = longitudes[0] if longitudes else None
    # Use the highest rating
    ratings = [info['exifInfo']['rating'] for info in asset_infos if info['exifInfo']['rating'] is not None]
    st.session_state["rating"] = max(ratings) if ratings else None
    # Use the original live photo video ID
    st.session_state["livePhotoVideoId"] = best_image_infos['livePhotoVideoId']
    # Frefer the visibility that is the most restrictive
    if any(info['visibility'] == 'locked' for info in asset_infos):
        st.session_state["visibility"] = 'locked'
    elif any(info['visibility'] == 'hidden' for info in asset_infos):
        st.session_state["visibility"] = 'hidden'
    elif any(info['visibility'] == 'archive' for info in asset_infos):
        st.session_state["visibility"] = 'archive'
    else:
        st.session_state["visibility"] = 'timeline'
    # Get the IDs of the images to delete
    image_ids_to_delete = [asset['id'] for asset in assets if asset['id'] != best_image_infos['id']]
    st.session_state.metadata_merged = True
    return best_image_infos["id"], image_ids_to_delete


def set_state(key: str, value):
    logger.info(f"Setting session state: {key} = {value}")
    st.session_state[key] = value

def set_state_location(latitude: str, longitude: str):
    logger.info(f"Setting {latitude=} and {latitude=}")
    st.session_state["latitude"] = latitude
    st.session_state["longitude"] = longitude


def next_duplicate():
    st.session_state.duplicate_number = st.session_state.duplicate_number + 1
    st.session_state.metadata_merged = False
    st.session_state['image_files'] = {}


def display_duplicates():
    progress_bar = st.progress(0, text="Processing duplicates ...")
    duplicates = st.session_state.duplicates[st.session_state.duplicate_number]
    progress_bar.progress(st.session_state.duplicate_number / st.session_state.duplicates_count, text=f"Processing duplicates {st.session_state.duplicate_number} / {st.session_state.duplicates_count}")
    duplicate_assets = duplicates['assets']
    if not st.session_state.get("metadata_merged", False):
        selected_metadata(duplicate_assets)
    columns = st.columns(len(duplicate_assets) + 1, vertical_alignment="center")
    for column_number, asset in enumerate(duplicate_assets):
        asset_info = immich.get_asset_info(asset['id'])
        with columns[column_number]:
            resolution = immich.ImageResolution.THUMBNAIL if "thumbnail" in st.session_state.load_image_quality.lower() else immich.ImageResolution.ORIGINAL
            key = f"{column_number}_{resolution.value}"
            if not key in st.session_state['image_files']:
                st.session_state['image_files'][key] = immich.get_asset_image(asset["id"], resolution)
            st.image(st.session_state['image_files'][key])
            currently_selected_image = st.session_state["keepImageId"] == asset['id']
            st.button(":green[Selected✅]" if currently_selected_image else "Keep image", disabled=True if currently_selected_image else False, on_click=set_state, args=["keepImageId", asset['id']], key=asset["id"])
            st.caption(asset['originalFileName'])

            date_time_original = asset_info["exifInfo"]["dateTimeOriginal"]
            st.button(f":green[{date_time_original}]" if datetime.fromisoformat(date_time_original) == datetime.fromisoformat(st.session_state["dateTimeOriginal"]) else f"{date_time_original}", key=f"{asset['id']}date_time_original", type="tertiary", on_click=set_state, args=["dateTimeOriginal", date_time_original])
            if st.session_state["latitude"] is not None and st.session_state["longitude"] is not None:
                with st.container(height=300):
                    currently_selected_location = st.session_state["latitude"] == asset_info["exifInfo"]["latitude"] and st.session_state["longitude"] == asset_info["exifInfo"]["longitude"]
                    if asset_info["exifInfo"]["latitude"] and asset_info["exifInfo"]["longitude"]:
                        df = pd.DataFrame(
                            [[asset_info["exifInfo"]["latitude"], asset_info["exifInfo"]["longitude"]]],
                            columns=["lat", "lon"],
                        )
                        st.map(df, height=200)
                        st.button(":green[Selected✅]" if currently_selected_location else "Select location", key=f"{asset['id']}{asset_info["exifInfo"]["latitude"]}", disabled=True if currently_selected_location else False, on_click=set_state_location, args=[asset_info["exifInfo"]["latitude"], asset_info["exifInfo"]["longitude"]])
            rating = asset_info['exifInfo']['rating']
            st.button(f":green[Rating: {rating}]" if rating == st.session_state["rating"] else f"Rating: {rating}", key=f"{asset['id']}rating", type="tertiary", on_click=set_state, args=["rating", rating])
            visibility = asset_info['visibility']
            st.button(f":green[Visibility: {visibility}]" if visibility == st.session_state["visibility"] else f"Visibility: {visibility}", key=f"{asset['id']}visibility", type="tertiary", on_click=set_state, args=["visibility", visibility])
            
            is_favorite = asset_info['isFavorite']
            st.button(f":green[Is Favorite: {is_favorite}]" if is_favorite == st.session_state["isFavorite"] else f"Is Favorite: {is_favorite}", key=f"{asset['id']}isFavorite", type="tertiary", on_click=set_state, args=["isFavorite", is_favorite])

            st.caption(f"Is Archived: {asset['isArchived']}")
            st.caption(f"Is Trashed: {asset['isTrashed']}")
            st.caption(f"Description: {asset['exifInfo']["description"]}")
    with columns[-1]:
        st.button("Skip", icon=":material/double_arrow:", on_click=next_duplicate)
        st.button("Apply", icon=":material/check:", on_click=next_duplicate)


def load_duplicates_from_server() -> int:
    if st.session_state.duplicates is None:
        print("fetching...")
        with st.spinner('Fetching assets from server...'):
            st.session_state.duplicates = immich.get_duplicates()
            st.session_state.duplicates_count = len(st.session_state.duplicates) if st.session_state.duplicates else 0
            logging.info(f"Loaded {st.session_state.duplicates_count} assets with duplicates from server.")
