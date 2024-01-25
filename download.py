#!/usr/bin/env python3

# https://github.com/saghetti0/obsidian-publish-downloader
# This software is licensed under the MIT License
# See (https://opensource.org/license/mit/)

import requests
import os
from tqdm import tqdm
import sys
import re
import json
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor

def download_file(url, path):
    resp = requests.get(url)
    parent_folder = os.path.dirname(os.path.abspath(path))
    if not os.path.exists(parent_folder):
        os.makedirs(parent_folder)
    with open(path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=1048576):
            f.write(chunk)

if len(sys.argv) < 3:
    print(f"Usage: {sys.argv[0]} URL FOLDER")
    exit(1)

try:
    main_page = requests.get(sys.argv[1]).text
except requests.exceptions.RequestException as e:
    print(f"Error fetching URL: {e}")
    exit(1)

match_siteinfo = re.findall('window\\.siteInfo\\s*=\\s*({[^}]+})', main_page)
if len(match_siteinfo) == 0:
    print("Unable to extract siteInfo")
    exit(1)

siteinfo = json.loads(match_siteinfo[0])
uid = siteinfo["uid"]
host = siteinfo["host"]

try:
    response = requests.get(f"https://{host}/cache/{uid}")
    response.raise_for_status()
    cache_data = response.json()
except requests.exceptions.HTTPError as err:
    print(f"HTTP error occurred: {err}")
    exit(1)
except json.JSONDecodeError:
    print("Invalid JSON response received:")
    print(response.text)
    exit(1)

download_tasks = [(f"https://{host}/access/{uid}/{i}", os.path.join(sys.argv[2], i)) for i in cache_data.keys()]

with ThreadPoolExecutor(max_workers=10) as executor:
    futures = [executor.submit(download_file, url, path) for url, path in download_tasks]

    for future in tqdm(concurrent.futures.as_completed(futures), total=len(download_tasks)):
        future.result()
