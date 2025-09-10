# **📸 Advanced Web Page Scraper & Archiver**

A local web application for automatically capturing screenshots, creating full-page MHTML archives, and processing PDF files from a list of URLs, with seamless uploading to a shared Google Drive.

## **Key Features**

* **Multiple Capture Modes:**  
  * Visible viewport screenshots.  
  * Full-page screenshots (with intelligent auto-scrolling).  
  * Full offline page archives in MHTML format.  
* **Responsive Testing:**  
  * Capture screenshots at different viewport widths (e.g., 1920px and 1280px).  
* **PDF Processing:**  
  * Download and save PDF files directly from URLs.  
  * Generate a PNG screenshot of the first page of a PDF.  
* **Smart Automation:**  
  * Uses a single persistent browser session for a batch of URLs, preserving cookies and login states.  
  * Automatically handles and closes cookie consent banners using a robust XPath selector.  
* **Cloud Integration:**  
  * Uploads all generated files (PNG, MHTML, PDF) to a specified shared folder in Google Drive.  
* **Simple Web UI:**  
  * An intuitive local web interface to input URLs, select options, and monitor progress in real-time.

## **Prerequisites**

Before you begin, ensure you have the following installed:

1. **Python 3.11+**  
2. **Poppler:** A PDF rendering library required for creating screenshots from PDF files.  
   * **Windows:** Download the latest release from [this page](https://github.com/oschwartz10612/poppler-windows/releases), and unzip it to a stable location (e.g., C:\\poppler).

## **Setup & Configuration**

Follow these steps to configure the project for its first run.

### **1\. Install Dependencies**

It is highly recommended to use a virtual environment.

```bash
# 1. Create and activate a virtual environment
python -m venv .venv
# On Windows
.\.venv\Scripts\activate
# On macOS/Linux
# source .venv/bin/activate

# 2. Install required Python packages
pip install -r requirements.txt

# 3. Download the necessary browser binaries for Playwright
playwright install
```

### **2\. Configure Project Files**

You need to edit three files to set up your specific paths and credentials.

1. **Google Drive API Credentials (credentials.json)**  
   * Go to the [Google Cloud Console](https://console.cloud.google.com/) and create OAuth 2.0 credentials for a Desktop application.  
   * Download the credentials file and save it as credentials.json in the root directory of the project.  
   * On the first run, the application will open a browser window asking you to authorize access to your Google account. A token.pickle file will be created to store your authorization for future sessions.  
2. **Google Drive Folder ID (upload\_to\_shared\_drive.py)**  
   * Open the upload\_to\_shared\_drive.py file.  
   * Find the line SHARED\_DRIVE\_FOLDER\_ID \= "...".  
   * Replace ... with the actual ID of the shared Google Drive folder where you want to upload the files.  
3. **Poppler Path (screenshot\_playwright.py)**  
   * Open the screenshot\_playwright.py file.  
   * Find the line poppler\_path \= r"C:\\path\\to\\your\\poppler\\bin".  
   * **Replace the path** with the correct path to the bin directory inside your Poppler installation folder. For example: poppler\_path \= r"C:\\poppler\\poppler-24.08.0\\Library\\bin".

## **Running the Application**

1. Make sure your virtual environment is activated.  
2. Run the Flask server from your terminal:
   ```bash  
   python app\local.py
   ```
4. The console will show that the server is running on http://127.0.0.1:5000.

## **How to Use**

1. Open the docs/index\_local.html file in your web browser.  
2. **Fill out the form:**  
   * **Site Name:** Used for naming the output folder in Google Drive.  
   * **Web Pages / PDF Files:** Paste the URLs you want to process into the appropriate text areas, one URL per line.  
   * **Processing Options:** Select the actions you want to perform.  
   * **Cookie Options:** If the websites have a cookie banner, check the box and provide the exact text from the consent button (e.g., Accept all).  
3. Click the **"Start"** button.  
4. Monitor the progress in the status log that appears below the form. When the task is complete, a link to the Google Drive folder will be displayed.

## **Troubleshooting**

* **Google Auth Error / token.pickle is stale:**  
  * Simply delete the token.pickle file from the project root and restart app\_local.py. The app will prompt you to re-authorize.  
* **"Poppler not found" / PDF screenshots fail:**  
  * Double-check that the poppler\_path variable in screenshot\_playwright.py points to the correct bin directory of your Poppler installation.  
* **Files not uploading to Google Drive:**  
  * Ensure credentials.json is correct and present in the project root.  
  * Verify that the SHARED\_DRIVE\_FOLDER\_ID in upload\_to\_shared\_drive.py is correct and that your Google account has write permissions for that folder.
