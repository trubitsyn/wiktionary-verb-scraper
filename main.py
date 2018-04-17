import argparse
import csv
import unicodedata

import requests
from bs4 import BeautifulSoup


def query_pages():
    request = {'format': 'json',
               'action': 'query',
               'list': 'categorymembers',
               'cmtitle': 'Категория:Русские_глаголы'}

    last_continue = {'continue': ''}

    while True:
        req = request.copy()
        req.update(last_continue)
        response = requests.get('https://ru.wiktionary.org/w/api.php', params=req).json()

        if 'error' in response:
            raise ValueError(response['error'])
        if 'warnings' in response:
            print(response['warnings'])
        if 'query' in response:
            yield response['query']
        if 'continue' not in response:
            break
        last_continue = response['continue']


def parse_page(id):
    url = 'https://ru.wiktionary.org/wiki/'
    doc = requests.get(url, params={'curid': id}).content
    soup = BeautifulSoup(doc, 'html.parser')
    tables = soup.findAll('table', {'rules': 'all'})

    if not tables:
        return None

    verb_forms = tables[0]
    rows = verb_forms.findAll('tr')[1:]
    forms = []

    for row in rows:
        columns = row.findAll('td')[1:]

        for item in columns:
            for span in item.findAll('span'):
                span.unwrap()

            for td in item.findAll('td'):
                td.unwrap()

            text = sanitize(item.text)

            if '\n' in text:
                forms.extend(text.split('\n'))
            else:
                forms.append(text)

    return {
        'present_i': forms[0],
        'present_thou': forms[4],
        'present_it': forms[8],

        'present_we': forms[13],
        'present_you': forms[16],
        'present_they': forms[19],

        'past_male': forms[9],
        'past_female': forms[10],
        'past_neutral': forms[11],
        'past_many': forms[14],
        'imperative': forms[7]
    }


def sanitize(word):
    return remove_accents(word).replace('△', '').replace('*', '')


def remove_accents(word):
    return ''.join((c for c in unicodedata.normalize('NFD', word) if unicodedata.category(c) != 'Mn'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Scrape Russian verb forms from Wiktionary.', add_help=True)
    parser.add_argument('--filename', type=str, default='verbs.csv',
                        help='file to save verb forms to (default: verbs.csv)')

    args = parser.parse_args()
    filename = args.filename

    with open(filename, 'w', newline='') as f:
        TOTAL_PAGES = 34704
        counter = 0
        w = None

        for response in query_pages():
            for e in response['categorymembers']:
                pageid = e['pageid']
                verb = parse_page(pageid)

                if verb is None:
                    continue

                if counter == 0:
                    w = csv.DictWriter(f, verb.keys())
                    w.writeheader()

                w.writerow(verb)

                counter += 1
                progress = round(counter / TOTAL_PAGES * 100)
                print(f'{progress}% {e}')
