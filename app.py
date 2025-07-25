import streamlit as st
import logging

from startup import setup_sidebar
import imageDuplicate
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Set page title and favicon
st.set_page_config(page_title="Immich DeDuper ", page_icon="https://immich.app/img/immich-logo-stacked-dark.svg", layout="wide")


def setup_session_state():
    """Initialize session state with default values."""
    session_defaults = {
        'duplicates_count': 0,
        'duplicate_number': 0,
        'duplicates': None,
        'image_files': {},
    }
    for key, default_value in session_defaults.items():
        if key not in st.session_state:
            logger.info(f"Setting default value for {key}: {default_value}")
            st.session_state[key] = default_value


def main():
    setup_session_state()
    setup_sidebar()
    if st.session_state.immich_api_connected:
        imageDuplicate.load_duplicates_from_server()
        if st.session_state.duplicates:
            imageDuplicate.display_duplicates()


if __name__ == "__main__":
    main()