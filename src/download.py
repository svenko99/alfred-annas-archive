import requests
from bs4 import BeautifulSoup
import sys
from pathlib import Path
import re

def clean_filename(filename):
    # Remove or replace characters that are illegal in macOS filenames
    illegal_chars = r'[/\\?%*:|"<>]'
    cleaned_name = re.sub(illegal_chars, '_', filename)
    
    # Remove leading/trailing spaces and periods
    cleaned_name = cleaned_name.strip('. ')
    
    # Ensure the filename is not empty
    if not cleaned_name:
        cleaned_name = '_'
    
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
        title = clean_filename(title)  # Clean the title
        with open(f"{download_path}/{title}{filetype}", "wb") as f:
            f.write(requests.get(download_link, allow_redirects=True).content)
        return f"Downloaded {title}{filetype}"


def main():
    md5, title, filetype = " ".join(sys.argv[1:]).split("#")
    try:
        print(resolve_libgen_download_link(md5, title, filetype))
    except Exception as e:
        print("Download failed. Please ensure the book source contains /lgli.")


if __name__ == "__main__":
    main()
