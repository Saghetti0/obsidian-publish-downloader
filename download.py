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

if len(sys.argv) < 3:
    print(f"Usage: {sys.argv[0]} URL FOLDER")
    exit(1)

main_page = requests.get(sys.argv[1]).text

match_siteinfo = re.findall('window\.siteInfo\s*=\s*({[^}]+})', main_page)

if len(match_siteinfo) == 0:
    print("Unable to extract siteInfo")
    exit(1)

siteinfo = json.loads(match_siteinfo[0])

uid = siteinfo["uid"]
host = siteinfo["host"]

cache_data = requests.get(f"https://{host}/cache/{uid}").json()

for i in tqdm(cache_data.keys()):
    resp = requests.get(f"https://{host}/access/{uid}/{i}")

    path = os.path.join(sys.argv[2], i)
    parent_folder = os.path.dirname(os.path.abspath(path))

    if not os.path.exists(parent_folder):
        os.makedirs(parent_folder)

    with open(path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=1048576): 
            f.write(chunk)
