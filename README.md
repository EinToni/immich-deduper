# Immich DeDuper

## A simple solution for deduplicating assets while preserving wanted metadata.

The "Immich DeDuper" is an tool designed to seamlessly be integrated with the Immich API.
It helps deduplicating images while preserving the metadata of your chosing. The metadata that is selected in the UI will be applied to the remaining deduplicated image, whether it stems from the original or a duplicate.

[!WARNING]
External libraries are currently not supported and could provide unknown behavior.


### Selectable and automatic preselection of metadata:
Specific metadata (that is supported by the [immich API](https://immich.app/docs/api/update-asset)) is selectable to be applied to the final image.

- **Creation Date/Time:** Choose the oldest timestamp as this is most often the most accurate and more recent timestamps are dues to later copying/modification/etc.
- **Description:** All descriptions are automatically appended to one another.
- **Is Favorite State:** If any image is selected as favorite.
- **Location:** The location of the first image is selected. If there are multiple locations available the user should intervene and select.
- **Live Photo ID Reference:** Won't be modified and won't be displayed.
- **Rating:** The highest rating will be chosen.
- **Visibility:** The most restricted will be chosen.

### Limitations:
I would love to provide more selections of metadata but the [immich API](https://immich.app/docs/api/update-asset) does not provide anything more. Therefore things like Tags are not available to modify


## Getting Started

"Immich DeDuper" is built as a Streamlit app in Python, making it easy to deploy and use with just a few steps. Follow these instructions to get up and running:

### Ensure Python 3.11 or newer is installed

[Python](https://www.python.org/downloads/) should be installed.

### Clone the Repository

Begin by cloning this repository to your local machine. You can do this by running the following command in your terminal or command prompt:

```bash
git clone https://github.com/EinToni/immich-deduper.git
```

### Install Dependencies

Navigate to the cloned repository's directory and install the required dependencies using the provided `requirements.txt` file:

```bash
cd immich-deduper
pip install -r requirements.txt
```
This command installs all necessary Python packages that "Immich Duplicate Finder" relies on.

### Launch the App
With the dependencies installed, you can now launch the Streamlit app. Execute the following command:
```bash
streamlit run app.py
```
This will start the Streamlit server and automatically open your web browser to the app's page. Alternatively, Streamlit will provide a local URL you can visit to view the app.

## Disclaimer

This software is provided "as is", without any warranty of any kind, express or implied, including but not limited to the warranties of merchantability, fitness for a particular purpose, and non-infringement. In no event shall the authors or copyright holders be liable for any claim, damages, or other liability, whether in an action of contract, tort, or otherwise, arising from, out of, or in connection with the software or the use or other dealings in the software.

This program is still under development and may contain bugs or defects that could lead to data loss or damage. Users are cautioned to use it at their own risk. The developers assume no responsibility for any damages, loss of information, or any other kind of loss resulting from the use of this program.
