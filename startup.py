import streamlit as st
import immich
import json
import os

SETTINGS_FILE = 'settings.json'
default_settings = {
    "immich_server_url": "",
    "immich_api_key": "",
    "request_timeout": 2000
}


def load_settings():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, 'r') as f:
            return json.load(f)
    else:
        return default_settings.copy()


def load_settings_info_streamlit():
    if 'settings_loaded' not in st.session_state:
        settings = load_settings()
        st.session_state['immich_server_url'] = settings.get(
            'immich_server_url', '')
        st.session_state['immich_api_key'] = settings.get('immich_api_key', '')
        st.session_state['request_timeout'] = settings.get(
            'request_timeout', 2000)
        st.session_state['settings_loaded'] = True


def save_settings():
    with open(SETTINGS_FILE, 'w') as f:
        settings = {
            "immich_server_url": st.session_state.immich_server_url,
            "immich_api_key": st.session_state.immich_api_key,
            "request_timeout": st.session_state.request_timeout
        }
        json.dump(settings, f, indent=4)


def setup_sidebar():
    st.sidebar.title("Immich DeDuper")
    st.sidebar.header("v0.1.0")
    st.sidebar.markdown("---")

    load_settings_info_streamlit()
    st.session_state.immich_server_reachable = False
    st.session_state.immich_api_connected = False
    expanded = False if st.session_state.immich_server_url and st.session_state.immich_api_key else True

    with st.sidebar.expander("Login Settings", expanded=expanded):
        st.text_input('IMMICH Server URL', key="immich_server_url", value=st.session_state.immich_server_url,
                                                           help="Enter the full URL to your immich instance, example: https://immich.mypage.com",
                                                           placeholder="https://immich.mypage.com").rstrip('/')
        if st.session_state.immich_server_url:
            st.session_state.immich_server_reachable = immich.ping_server()
            if not st.session_state.immich_server_reachable:
                st.sidebar.error('No connection to server possible.')

        st.session_state.immich_api_key = st.text_input(
            'API Key', st.session_state.immich_api_key, help="Enter your API key here. You can find it in the Immich web interface under Settings > API Keys: ")
        if st.session_state.immich_api_key:
            if st.session_state.immich_server_reachable:
                st.session_state.immich_api_connected = immich.is_api_key_valid()
                if not st.session_state.immich_api_connected:
                    st.sidebar.error(
                        'Cannot authenticate to server with given API-Key.')
        if st.session_state.immich_server_reachable and not st.session_state.immich_api_connected:
            st.link_button(
                'Create an API Key', url=st.session_state.immich_server_url + "/user-settings?isOpen=api-keys")

        st.number_input(
            'Request timeout (ms)', key="request_timeout", value=2000, min_value=10, max_value=10000)


        if st.session_state.request_timeout < 100 or 0:
            st.sidebar.warning(
                'Warning: Timeout is set very low. It may cause request failures.')

        if not st.session_state.immich_server_reachable:
            st.sidebar.badge("Server not available",
                             icon=":material/cloud_off:", color="red")
        elif st.session_state.immich_server_reachable and not st.session_state.immich_api_connected:
            st.sidebar.badge("Authentication error",
                             icon=":material/key_off:", color="orange")
        elif st.session_state.immich_api_connected:
            st.sidebar.badge(
                "Connected", icon=":material/check_circle:", color="green")
        save_settings()
    st.sidebar.markdown("---")
    st.sidebar.selectbox("Load image quality", ["Thumbnail (fast)", "Original (slow)"], key="load_image_quality",
                         help="Select the image quality to load. Thumbnail is faster but lower quality, Original is slower but full quality.")
