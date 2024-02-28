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
from concurrent.futures import ThreadPoolExecutor

# Initialize error log with UTF-8 encoding. Log includes the script execution
# argument which typically would be the URL being accessed.
error_log_filename = "error.log"
with open(error_log_filename, 'w', encoding='utf-8') as error_log_file:
    error_log_file.write("Error Log - {}\n----------------------\n".format(
        sys.argv[1]))

# Validate command-line arguments for the URL and download folder path.
if len(sys.argv) < 3:
    print("Usage: {} URL FOLDER".format(sys.argv[0]))
    sys.exit(1)


# Function to sanitize filenames by replacing invalid characters.
def sanitize_filename(filename):
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    return filename


# Function to download files, handling HTTP errors and writing content.
def download_file(file_info, session):
    i, file_url, base_path = file_info
    path_components = i.split('/')
    sanitized_components = [sanitize_filename(pc) for pc in path_components]
    sanitized_path = os.path.join(base_path, *sanitized_components)

    try:
        with session.get(file_url, stream=True) as resp:
            resp.raise_for_status()
            os.makedirs(os.path.dirname(sanitized_path), exist_ok=True)
            with open(sanitized_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
        return True, None
    except requests.exceptions.RequestException as e:
        error_message = "Error downloading: {}: {} {}".format(
            i, e.response.status_code, e.response.reason)
        return False, error_message


# Main execution block to process downloads.
try:
    main_page = requests.get(sys.argv[1]).text
    site_info_pattern = r'window\.siteInfo\s*=\s*({[^}]+})'
    match_siteinfo = re.findall(site_info_pattern, main_page)
    if not match_siteinfo:
        print("Unable to extract siteInfo")
        sys.exit(1)

    siteinfo = json.loads(match_siteinfo[0])
    uid, host = siteinfo["uid"], siteinfo["host"]

    cache_url = "https://{}/cache/{}".format(host, uid)
    cache_data = requests.get(cache_url).json()
    tasks = [(i, "https://{}/access/{}/{}".format(host, uid, i), sys.argv[2])
             for i in cache_data.keys()]

    print("\n-----------------\nStarting Download\n-----------------")

    errors = []
    downloaded_files_count = 0
    not_found_error_count = 0
    forbidden_error_count = 0
    server_error_count = 0
    too_many_requests_count = 0

    with tqdm(total=len(tasks), desc="Downloading files", unit="file") as pbar:
        with ThreadPoolExecutor(max_workers=3) as executor:
            with requests.Session() as session:
                futures = {executor.submit(download_file, t, session): t
                           for t in tasks}
                for future in futures:
                    success, error = future.result()
                    if not success:
                        errors.append(error)
                        error_code = error.split(":")[2].strip()
                        if "404" in error_code:
                            not_found_error_count += 1
                        elif "403" in error_code:
                            forbidden_error_count += 1
                        elif "500" in error_code:
                            server_error_count += 1
                        elif "429" in error_code:
                            too_many_requests_count += 1
                        tqdm.write(error + "\n-----------------")
                    else:
                        downloaded_files_count += 1
                    pbar.update(1)

    pbar.close()

    with open(error_log_filename, 'a', encoding='utf-8') as error_log_file:
        for error in errors:
            error_log_file.write("\n" + error + "\n-----------------")

        summary_lines = [
            "\n-----------------\nSummary:",
            "Initial file count: {}".format(len(tasks)),
            "Files downloaded: {}".format(downloaded_files_count)
        ]
        if not_found_error_count > 0:
            summary_lines.append("404 Not Found Errors: {}".format(
                not_found_error_count))
        if forbidden_error_count > 0:
            summary_lines.append("403 Forbidden Errors: {}".format(
                forbidden_error_count))
        if server_error_count > 0:
            summary_lines.append("500 Internal Server Errors: {}".format(
                server_error_count))
        if too_many_requests_count > 0:
            summary_lines.append("429 Too Many Requests Errors: {}".format(
                too_many_requests_count))
        summary_lines.append("-----------------\n")

        summary = "\n".join(summary_lines)
        print(summary)
        error_log_file.write(summary)

except Exception as e:
    print("An error occurred: {}".format(e))
    with open(error_log_filename, 'a', encoding='utf-8') as error_log_file:
        error_log_file.write("\n-----------------\nAn error occurred: {}\n"
                             "-----------------\n".format(e))
