import os
import sys
from pathlib import Path
import re
import requests
from bs4 import BeautifulSoup

def clean_filename(filename):
    # Remove or replace characters that are illegal in macOS filenames
    illegal_chars = r'[/\\?%*:|"<>]'
    cleaned_name = re.sub(illegal_chars, '_', filename)

    # Remove leading/trailing spaces and periods
    cleaned_name = cleaned_name.strip('. ')

    # Ensure the filename is not empty
    if not cleaned_name:
        cleaned_name = 'Book'

    return cleaned_name

def resolve_libgen_download_link(md5, title, filetype):
    link = f"http://libgen.li/ads.php?md5={md5}"
    response = requests.get(link)
    soup = BeautifulSoup(response.text, "html.parser")
    download_link = soup.find_all("a")
    download_link = (
        "http://libgen.li/"
        + [link["href"] for link in download_link if "get.php" in link["href"]][0]
    )
    if response.status_code == 200:
        download_path = str(Path.home() / "Downloads")

        # Clean the title to ensure it is a valid filename
        title = clean_filename(title)

        # Create filename and path and check for file conflicts
        base_filename = f"{title}{filetype}"
        full_path = os.path.join(download_path, base_filename)
        counter = 1    
        while os.path.exists(full_path):
            base_filename = f"{title}_{counter}{filetype}"
            full_path = os.path.join(download_path, base_filename)
            counter += 1
        
        # Download and save the file
        with open(full_path, "wb") as f:
            f.write(requests.get(download_link, allow_redirects=True).content)
        
        return f"Downloaded {base_filename}"


def main():
    md5, title, filetype = " ".join(sys.argv[1:]).split("#")
    try:
        print(resolve_libgen_download_link(md5, title, filetype))
    except Exception as e:
        print("Download failed. Please ensure the book source contains /lgli.")


if __name__ == "__main__":
    main()
