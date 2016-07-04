import os
from textwrap import TextWrapper
from pprint import pprint
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
import json

# with open('config.json', 'r') as f:
#     config = json.load(f)
#
# #edit the data
# config['key3'] = 'value3'
#
# #write it back to the file
# with open('config.json', 'w') as f:
#     json.dump(config, f)

settings = dict(
    ext_file='txt',

    header_elem='h1',
    header_attrs={'class': 'b-topic__title'},

    article_elem='div',
    article_attrs={'itemprop': 'articleBody'},
    article_indent='\n\n',

    sub_article_elem='p',
    text_width=80,
)

wrapper = TextWrapper(width=settings['text_width'])


class MainProgram:
    @staticmethod
    def run():
        response = requests.get('https://lenta.ru/news/2016/07/01/vapersong/')
        parsed_html = BeautifulSoup(response.text, "html.parser")
        text = ''
        header = wrapper.fill(parsed_html.find(settings['header_elem'], settings['header_attrs']).get_text())
        text += header
        wrapper.initial_indent = settings['article_indent']
        for paragraph in parsed_html \
                .find(settings['article_elem'], settings['article_attrs']) \
                .find_all(settings['sub_article_elem']):
            for link in paragraph.find_all('a'):
                link.replace_with('{}[{}]'.format(link.get_text(), link['href']))
            text += wrapper.fill(paragraph.text.strip())

        final_url = urlparse(response.url)
        filename = '{}{}.{}'.format(final_url.netloc, final_url.path[:-1], settings['ext_file'])
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, "w") as f:
            f.write(text)


if __name__ == "__main__":
    MainProgram.run()
