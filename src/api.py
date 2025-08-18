import requests
from bs4 import BeautifulSoup
import json
import sys
import os
import re

KEYWORD = sys.argv[1]
CUSTOM_SUBTITLE = os.getenv("CUSTOM_SUBTITLE", "{0} | {1} | {2} | {3} | {4} | {5}")
LANGUAGES = os.getenv("LANGUAGES", None)  # Comma-separated list of languages
SOURCE_FILTER = bool(int(os.getenv("SOURCE_FILTER"), 0))
ORDER_BY = os.getenv("ORDER_BY", "None")
CUSTOM_SUBTITLE_VARIABLES = {
    "{0}": "authors",
    "{1}": "book_lang",
    "{2}": "book_filetype",
    "{3}": "book_source",
    "{4}": "book_size",
    "{5}": "book_content",
}
# fmt: off
AVAILABLE_LANGUAGES = [
    "en", "ru", "de", "es", "it", "zh", "fr", "hu", "ja", "pt", "la", "hi",
    "nl", "lb", "bn", "ur", "id", "ar", "el", "he", "ko", "zxx", "bg", "pl",
    "fa", "ta", "af", "tr", "uk", "kn", "sv", "da", "ro", "vi", "fil", "sa",
    "ml", "mr", "cs", "hr", "grc", "sr", "ndl", "ga", "fi", "ca", "cy", "lv",
    "jv", "bo", "lt", "cu", "be", "sce", "kk", "no", "mn", "ka", "sl", "eo",
    "sk", "gl", "rw", "gu", "et", "az", "sve", "ms"
]


# fmt: on


def create_custom_subtitle(subtitle_format, variables, result):
    subtitle = subtitle_format
    for key, value in variables.items():
        if value in result:
            subtitle = subtitle.replace(key, result[value])
    return subtitle


def parse_sub_results(sub_results_text):
    # Split by commas and strip whitespace from each part
    parts = [part.strip() for part in sub_results_text.split(",")]

    # Regular expression to detect language tags in the format "[xx]"
    lang_pattern = re.compile(r"\[[a-z]{2}\]")

    # Initialize variables with default values
    book_lang = "Unknown Language"
    book_filetype = "Unknown Filetype"
    book_source = "Unknown Source"
    book_size = "Unknown Size"
    book_content = "Unknown Content"

    # Check if language information is present in parts[0] and parts[1]
    if (
            len(parts) > 1
            and lang_pattern.search(parts[0])
            and lang_pattern.search(parts[1])
    ):
        # Combine the first two parts as the language information
        book_lang = f"{parts[0]}, {parts[1]}"
        other_parts = parts[2:]
    elif lang_pattern.search(parts[0]):
        # Language is only in parts[0]
        book_lang = parts[0]
        other_parts = parts[1:]
    else:
        # No language information detected, start parsing from the beginning
        other_parts = parts

    # Assign the remaining fields if available
    if len(other_parts) > 0:
        book_filetype = other_parts[0]
    if len(other_parts) > 1:
        book_source = other_parts[1]
    if len(other_parts) > 2:
        book_size = other_parts[2]
    if len(other_parts) > 3:
        book_content = other_parts[3]

    return book_lang, book_filetype, book_source, book_size, book_content


def create_url(query, page=1, order_by="", langs=None):
    # Check if the first word of the query is a language code
    query_parts = query.split(" ")
    live_lang_param = query_parts[0]

    if live_lang_param in AVAILABLE_LANGUAGES and len(live_lang_param) <= 3:
        lang_params = f"&lang={live_lang_param}"
        query = " ".join(query_parts[1:])
    else:
        # Generate lang_params from provided langs
        lang_params = (
            "".join(
                [
                    f"&lang={lang.strip()}"
                    for lang in langs.split(",")
                    if lang.strip() in AVAILABLE_LANGUAGES
                ]
            )
            if langs
            else ""
        )

    return f"https://annas-archive.org/search?index=&page={page}&q={query}&sort={order_by}{lang_params}"


def get_search_results(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")

    # Find the container holding all search results
    results_container = soup.find("div", class_="js-aarecord-list-outer")
    if not results_container:
        return []

    # Each search result is a flex div inside the container
    results = results_container.find_all("div", class_="flex")

    search_results = []
    for result in results:
        # Book link (MD5 page)
        link_tag = result.find("a", href=True)
        if not link_tag:
            continue
        link = "https://annas-archive.org" + link_tag["href"]

        # Title of the book
        title_tag = result.find("a", class_="js-vim-focus")
        title = title_tag.text.strip() if title_tag else "Unknown Title"

        # Author(s)
        author_tag = result.find("span", class_="icon-[mdi--user-edit]")
        authors = author_tag.parent.text.strip() if author_tag else "Unknown Author"
        if len(authors) > 50:
            authors = authors[:50] + "..."

        # Publisher / Publication info
        publisher_tag = result.find("span", class_="icon-[mdi--company]")
        publication = publisher_tag.parent.text.strip() if publisher_tag else ""

        # Metadata line (language, filetype, size, year, content, source)
        meta_line = result.find("div", class_="text-gray-800")
        book_lang, book_filetype, book_size, book_year, book_content, book_source = (
            "Unknown Language",
            "Unknown Filetype",
            "Unknown Size",
            "Unknown Year",
            "Unknown Content",
            "Unknown Source",
        )
        if meta_line:
            parts = [p.strip() for p in meta_line.text.split("·")]
            if len(parts) > 0: book_lang = parts[0]
            if len(parts) > 1: book_filetype = parts[1]
            if len(parts) > 2: book_size = parts[2]
            if len(parts) > 3: book_year = parts[3]
            if len(parts) > 4: book_content = parts[4]
            if len(parts) > 5: book_source = parts[5]

        search_results.append({
            "link": link,
            "title": title,
            "authors": authors,
            "publication": publication,
            "book_lang": book_lang,
            "book_filetype": book_filetype,
            "book_size": book_size,
            "book_year": book_year,
            "book_content": book_content,
            "book_source": book_source,
            "md5": link.split("/")[-1],
        })

    return search_results


def output_results(results):
    return json.dumps({"items": results})


def create_alfred_item(
        title, subtitle=None, arg=None, quicklookurl=None, md5=None, filetype=None
):
    return {
        "title": title,
        "subtitle": subtitle,
        "arg": arg,
        "quicklookurl": quicklookurl,
        "mods": {
            "cmd": {
                "valid": True,
                "arg": f"{md5}#{title}#{filetype}",
            }
        },
    }


def build_alfred_results(url, results):
    alfred_items = []
    if results:
        for result in results:
            # Remove the rocket emoji (U+1F680)
            book_source = re.sub("\U0001f680", "", result["book_source"])
            # Filter out non-Libgen sources only if SOURCE_FILTER=True
            if not SOURCE_FILTER or book_source.startswith("/lgli"):
                custom_subtitle = create_custom_subtitle(
                    CUSTOM_SUBTITLE, CUSTOM_SUBTITLE_VARIABLES, result
                )
                alfred_item = create_alfred_item(
                    title=result["title"],
                    subtitle=custom_subtitle,
                    arg=result["link"],
                    quicklookurl=result["link"],
                    md5=result["md5"],
                    filetype=result["book_filetype"],
                )
                alfred_items.append(alfred_item)
    else:
        alfred_items.append(
            create_alfred_item(
                title="No results found",
                subtitle="Look for partial matches",
                arg=url,
                quicklookurl=url,
            )
        )

    print(output_results(alfred_items))


def main(query, page=1, order_by="", langs=None):
    url = create_url(query, page, order_by, langs)
    # print("url:", url)
    results = get_search_results(url)
    build_alfred_results(url, results)


if __name__ == "__main__":
    main(KEYWORD, order_by=ORDER_BY, langs=LANGUAGES)
