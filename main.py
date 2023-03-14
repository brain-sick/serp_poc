import pandas as pd
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs
from time import time
import logging
import tldextract
import re
import sys
import os

logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO)

SERP_DIV_CLASS = "yuRUbf"


def extract_websites_from_linkedin():
    soup = BeautifulSoup(unblocker_res.text, 'html.parser')
    tag = soup.find('a', {'data-tracking-control-name': 'about_website'})
    text = tag.text.strip()
    website_list = [text]
    return website_list


def extract_websites_from_playstore():
    soup = BeautifulSoup(unblocker_res.text, 'html.parser')
    website_list = set()
    for div in soup.find_all('div', {'class': 'pZ8Djf'}):
        if div.find('div', {'class': 'xFVDSb'}).text in ['Website', 'Email', 'Privacy policy']:
            website_list.add(div.find('div', {'class': 'pSEeg'}).text)
    return list(website_list)


def extract_websites_from_pitchbook():
    soup = BeautifulSoup(unblocker_res.text, 'html.parser')
    a_tag = soup.find("a", {"class": "d-block-XL font-underline", "aria-label": "Website link"})
    return [a_tag["href"]]


def extract_websites_from_appstore():
    soup = BeautifulSoup(unblocker_res.text, 'html.parser')
    website_list = set()
    for a in soup.find_all('a', {'class': 'link icon icon-after icon-external'}):
        if 'Developer Website' in a.text or 'App Support' in a.text or 'Privacy Policy' in a.text:
            website_list.add(a['href'])
    return list(website_list)


def extract_websites_from_glassdoor():
    soup = BeautifulSoup(unblocker_res.text, 'html.parser')
    a_tag = soup.find('a', {'data-test': 'employer-website'})
    return [a_tag["href"]]


def remove_ending_slash_from_url(url):
    if url[-1] == '/':
        url = url[:-1]
    return url


def serp_datasource_id_from_linkedin_url(url):
    url = remove_ending_slash_from_url(url)
    path = urlparse(url).path
    path = remove_ending_slash_from_url(path)
    data_source_ids = path.split('/')[-1]
    return data_source_ids


def serp_datasource_id_from_playstore_url(url):
    url = remove_ending_slash_from_url(url)
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)
    data_source_ids = query_params['id'][0]
    return data_source_ids


def serp_datasource_id_from_appstore_url(url):
    url = remove_ending_slash_from_url(url)
    path = urlparse(url).path
    data_source_ids = path.split('/')[-1]
    data_source_ids = str(data_source_ids).removeprefix('id')
    return data_source_ids


def serp_datasource_id_from_glassdoor_url(url):
    url = remove_ending_slash_from_url(url)
    url = url.removesuffix('.htm')
    path = urlparse(url).path
    last_part = str(path.split('/')[-1])
    match = re.search(r"EI_IE(\d+)\.", last_part)
    return match.group(1)


unblocker_dict = {
    'linkedin': extract_websites_from_linkedin,
    'playstore': extract_websites_from_playstore,
    'pitchbook': extract_websites_from_pitchbook,
    'appstore': extract_websites_from_appstore,
    'glassdoor': extract_websites_from_glassdoor
}

datasource_serp_id_extractor = {
    'linkedin': serp_datasource_id_from_linkedin_url,
    'playstore': serp_datasource_id_from_playstore_url,
    'pitchbook': serp_datasource_id_from_linkedin_url,
    'appstore': serp_datasource_id_from_appstore_url,
    'glassdoor': serp_datasource_id_from_glassdoor_url
}


def extract_url_from_serp_res():
    soup = BeautifulSoup(response.text, 'html.parser')
    div_list = soup.find_all('div', {'class': SERP_DIV_CLASS})
    unblocker_url_list = []
    for div in div_list:
        anchor_tag = div.find('a')
        unblocker_url_list.append(anchor_tag['href'])
    return unblocker_url_list


def create_output_file_entry():
    domain_matching = 'True' if domain == extracted_domain else 'False'
    _row = f'{company_id}, {data_source}, {domain}, "{unblocker_url}", {serp_data_source_id}, {website}, {extracted_domain}, {domain_matching}\n'
    file_name_dict[data_source].write(_row)


def extract_domain(url):
    ext = tldextract.extract(url)
    return f'{ext.domain}.{ext.suffix}'


if __name__ == '__main__':
    arg_length = len(sys.argv)
    if arg_length != 2:
        logging.error('Incorrect number of arguments')
        exit()

    index = sys.argv[1]
    df = pd.read_csv(os.path.join('input', f'input_{index}.csv'))
    base_start_time = time()
    associations = ['linkedin', 'glassdoor', 'pitchbook', 'playstore', 'appstore']
    file_name_dict = {}
    for association in associations:
        file_name_dict[association] = open(os.path.join('result', f'{association}_{index}.txt'), 'w+', 1)
    error_file = open(os.path.join('error', f'errors_{index}.txt'), 'w+', 1)
    success_file = open(os.path.join('success', f'success_{index}.txt'), 'w+', 1)

    session = requests.Session()
    for index, row in df.iterrows():
        start_time = time()
        domain = row['domain']
        company_id = row['company_id']
        data_source = row['entity']
        google_query = row['google_query']
        try:
            serp_url = "https://www.google.com/search?q=" + google_query.replace(' ', '+')

            serp_proxies = {
                "https": "https://brd-customer-hl_387a0b46-zone-serp_zone:7j5tinf2e6il@zproxy.lum-superproxy.io:22225",
            }

            response = session.get(serp_url, proxies=serp_proxies, verify=False, timeout=15)
            # it returns 10 results by default
            unblocker_urls = extract_url_from_serp_res()
            unblocker_proxies = {
                'https': 'http://brd-customer-hl_387a0b46-zone-unblocker_1:y1ibmxaapy29@zproxy.lum-superproxy.io:22225'
            }
            success_file.write(f'unblocker urls extracted for {domain}, {data_source}\n')
            logging.info(f'unblocker urls extracted for {domain}, {data_source}')
            for unblocker_url in unblocker_urls:
                try:
                    unblocker_res = session.get(unblocker_url, proxies=unblocker_proxies, verify=False, timeout=15)
                    serp_data_source_id = datasource_serp_id_extractor[data_source](unblocker_url)
                    websites = unblocker_dict[data_source]()
                    success_file.write(f'websites extracted from {unblocker_url}\n')
                    logging.info(f'websites extracted from {unblocker_url}')
                    for website in websites:
                        extracted_domain = extract_domain(website)
                        create_output_file_entry()
                except Exception as e:
                    logging.error(f'{company_id}, {domain}, {data_source}, {google_query}, {unblocker_url} : {str(e)}')
                    error_file.write(f'{company_id}, {domain}, {data_source}, {google_query}, {unblocker_url}: {str(e)}\n')

            end_time = time()
            success_file.write(f'{company_id}, {data_source}, Time taken: {end_time - start_time}\n')
            logging.info(f'{company_id}, {data_source}, Time taken: {end_time - start_time}')
        except Exception as e:
            logging.error(f'{company_id}, {domain}, {data_source}, {google_query} : {str(e)}')
            error_file.write(f'{company_id}, {domain}, {data_source}, {google_query} : {str(e)}\n')

    session.close()
    error_file.close()
    success_file.close()
    for file in file_name_dict.values():
        file.close()
    base_end_time = time()
    success_file.write(f'Total time take: {base_end_time - base_start_time}\n')
    logging.info(f'Total time take: {base_end_time - base_start_time}')
