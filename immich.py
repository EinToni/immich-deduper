import requests, json
import streamlit as st
from PIL import Image, UnidentifiedImageError, ImageFile
from io import BytesIO
from pillow_heif import register_heif_opener
import os
from enum import Enum
import logging
logger = logging.getLogger(__name__)


def ping_server() -> bool:
    try:
        response = requests.get(f"{st.session_state['immich_server_url']}/api/server/ping", headers={'Accept': 'application/json'}, timeout=1000)
        if response.ok:
            return True
    except:
        return False


def is_api_key_valid():
    if get_from_authenticated_api("system-config"):
        return True
    return False


@st.cache_data
def fetchAssets(immich_server_url, api_key, timeout, type):
    # Initialize messaging and progress
    if 'fetch_message' not in st.session_state:
        st.session_state['fetch_message'] = ""
    message_placeholder = st.empty()

    # Initialize assets to None or an empty list, depending on your usage expectation
    assets = []

    # Remove trailing slash from immich_server_url if present
    base_url = immich_server_url.rstrip('/')
    asset_info_url = f"{base_url}/api/asset/"
    
    try:
        with st.spinner('Fetching assets...'):
            # Make the HTTP GET request
            response = requests.get(asset_info_url, headers={'Accept': 'application/json', 'x-api-key': api_key}, verify=False, timeout=timeout)
            response.raise_for_status()  # This will raise an exception for HTTP errors
            
            content_type = response.headers.get('Content-Type', '')
            if 'application/json' in content_type:
                if response.text:
                    assets = response.json()  # Decode JSON response into a list of assets
                    assets = [asset for asset in assets if asset.get("type") == type]                       
                    st.session_state['fetch_message'] = 'Assets fetched successfully!'
                else:
                    st.session_state['fetch_message'] = 'Received an empty response.'
                    assets = []  # Set assets to empty list if response is empty
            else:
                st.session_state['fetch_message'] = f'Unexpected Content-Type: {content_type}\nResponse content: {response.text}'
                assets = []  # Set assets to empty list if unexpected content type

    except requests.exceptions.ConnectTimeout:
        st.session_state['fetch_message'] = 'Failed to connect to the server. Please check your network connection and try again.'
        assets = []  # Set assets to empty list on connection timeout

    except requests.exceptions.HTTPError as e:
        st.session_state['fetch_message'] = f'HTTP error occurred: {e}'
        assets = []  # Set assets to empty list on HTTP error

    except requests.exceptions.RequestException as e:
        st.session_state['fetch_message'] = f'Error fetching assets: {e}'
        assets = []  # Set assets to empty list on other request errors

    message_placeholder.text(st.session_state['fetch_message'])
    return assets

class ImageResolution(Enum):
    THUMBNAIL = "thumbnail"
    FULLSIZE = "fullsize"
    ORIGINAL = "original"

@st.cache_data(max_entries=25)
def get_asset_image(asset_id: str, resolution: ImageResolution):
    logger.debug(f"Fetching image for asset_id: {asset_id} with resolution: {resolution}")
    """Fetches an image for a given asset ID and resolution."""
    if resolution == ImageResolution.THUMBNAIL or resolution == ImageResolution.FULLSIZE:
        image = get_from_authenticated_api(f"assets/{asset_id}/thumbnail?size={resolution.value}", accept_type="octet-stream")
    else:
        image = get_from_authenticated_api(f"assets/{asset_id}/original", accept_type="octet-stream")
    if image:
        image_bytes = BytesIO(image.content)
        try:
            image = Image.open(image_bytes)
            image.load()
            return image
        except UnidentifiedImageError:
            logger.error(f"Failed to identify image for asset_id {asset_id}. Content-Type: {image.headers.get('Content-Type')}")
        finally:
            image_bytes.close()
    return None


def get_asset_info(asset_id: str) -> dict | None:
    """"Fetches asset information for a given asset ID."""
    info = get_from_authenticated_api(f"assets/{asset_id}")
    if info:
        return info.json()
    return None


def delete_assets(asset_ids: list[str]):
    payload = json.dumps({
        "ids": asset_ids
    })
    result = delete_authenticated_api("assets", payload)
    if result.status_code != 204:
        st.error(f"Failed to delete assets: {result.status_code} - {result.text}")


def update_asset(asset_id, metadata_to_update: dict):
    payload = json.dumps(metadata_to_update)
    result = put_authenticated_api(f"assets/{asset_id}", payload=payload)
    if result:
        logger.debug(f"Update asset resulted in: {result.json()}")


def get_duplicates():
    response = get_from_authenticated_api("duplicates", accept_type="octet-stream")
    if response:
        return response.json()
    return None


def get_from_authenticated_api(endpoint: str, accept_type="json") -> requests.Response | None:
    """Fetch data from the Immich API with API key."""
    if not st.session_state['immich_server_url'] or not st.session_state['immich_api_key']:
        logging.error(f"{st.session_state['immich_server_url']=} and {st.session_state['immich_api_key']=} must be set before making requests.")
        return None
    
    headers = {'Accept': f'application/{accept_type}',
               'x-api-key': st.session_state['immich_api_key']}

    return try_api_request("GET", endpoint, headers)


def put_authenticated_api(endpoint: str, payload=None) -> requests.Response | None:
    """Put data on the Immich API with API key."""
    if not st.session_state['immich_server_url'] or not st.session_state['immich_api_key']:
        logging.error(f"{st.session_state['immich_server_url']=} and {st.session_state['immich_api_key']=} must be set before making requests.")
        return None
    
    headers = {'Accept': 'application/json',
               'x-api-key': st.session_state['immich_api_key'],
               'Content-Type': 'application/json'}

    return try_api_request("PUT", endpoint, headers, payload)


def delete_authenticated_api(endpoint: str, payload=None) -> requests.Response | None:
    """Delete data from the Immich API with API key."""
    if not st.session_state['immich_server_url'] or not st.session_state['immich_api_key']:
        logging.error(f"{st.session_state['immich_server_url']=} and {st.session_state['immich_api_key']=} must be set before making requests.")
        return None
    
    headers = {'Content-Type': 'application/json',
               'x-api-key': st.session_state['immich_api_key']}
    
    return try_api_request("DELETE", endpoint, headers, payload)


def try_api_request(method: str, endpoint: str, headers, payload=None) -> requests.Response | None:
    url = f"{st.session_state['immich_server_url']}/api/{endpoint.lstrip('/')}"
    try:
        response = requests.request(method, url, headers=headers, data=payload, timeout=st.session_state['request_timeout'])
        logging.debug(f"Executing API call {method} {url=} with {headers=} and {payload=} returned status code: {response.status_code}")
        response.raise_for_status()
        return response
    except requests.exceptions.RequestException as e:
        logger.error(f"Error executing API call {method} {url}: {e}")
    return None
