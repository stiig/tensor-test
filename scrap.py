import argparse
import json
import urllib.request
import urllib.error

import operator
from html.parser import HTMLParser
from textwrap import TextWrapper
from urllib.parse import urlparse

import os
import re


class Settings:
    def __init__(self):
        self.settings = {}
        self.load()

    def load(self):
        try:
            with open('settings.json', 'r') as f:
                self.settings = json.load(f)
        except FileNotFoundError:
            raise Settings.SettingNotFound('File with settings not found, '
                                           'please create file settings.json')

    def get(self, elem):
        setting = self.settings.get(elem)
        if setting:
            return setting
        raise Settings.SettingNotFound('Setting not found ' + elem)

    class SettingNotFound(Exception):
        pass


class HTMLSourceParser(HTMLParser):
    """
    Здесь конроллируется вложенность тегов
    """
    def __init__(self, *, convert_charrefs=True):
        super().__init__(convert_charrefs=convert_charrefs)
        self.header_recording = 0
        self.div_recording = 0
        self.header_data = []
        self.div_data = {}

    def error(self, message):
        pass

    def handle_starttag(self, tag, attrs):
        if tag != 'h1' and tag != 'div' and tag != 'a':
            return

        if self.header_recording and tag == 'h1':
            self.header_recording += 1
            return
        if self.div_recording and tag == 'div':
            self.div_recording += 1
            return

        if tag == 'h1':
            self.header_recording = 1
        if tag == 'div':
            self.div_recording = 1

    def handle_endtag(self, tag):
        if tag == 'h1' and self.header_recording:
            self.header_recording -= 1
        if tag == 'div' and self.div_recording:
            self.div_recording -= 1

    def handle_data(self, data):
        if self.header_recording:
            self.header_data.append(data.strip())
        if self.div_recording and data.strip():
            inner_data = self.div_data.get(self.div_recording, [])
            inner_data.append(data.strip())
            self.div_data[self.div_recording] = inner_data


class Parser:
    """
    Основной разбор происходит в этом классе, при создании экземпляра класса
    так же задаются глобальные настройки. При помощи внутреннего парсера
    разбираем страницу, находим див который содержит больше всего дивов в себе
    и отдаем его как контент статьи.
    Для работы обязательно нужно задать настройки для домена
    """

    def __init__(self, raw_data, settings):
        self.page = raw_data
        self.settings = settings
        self.wrapper = TextWrapper(width=self.settings.get('text_width'))
        self.__parsed_title = None
        self.__parsed_content = None
        self.prepare()

    def prepare(self):
        removed_tags = [
            'script',
            'aside',
            'header',
            'style',
            'nav',
            'section',
            'footer',
            'noindex',
        ]

        result = self.page
        for tag in removed_tags:
            rx = "<{0}[\s\S]+?/{0}>".format(tag)
            pattern = re.compile(rx)
            result = re.sub(pattern, '', result)

        pattern_link = re.compile(r'<a\s+[^>]*?href="([^"]*)".*?>(.*?)<\/a>', re.DOTALL)
        result = pattern_link.sub(r'\2[\1]', result)

        inner_parser = HTMLSourceParser()
        inner_parser.feed(result)
        inner_parser.close()

        divs = {k: len(v) for k, v in inner_parser.div_data.items()}
        max_divs = max(divs.items(), key=operator.itemgetter(1))[0]

        self.__parsed_title = inner_parser.header_data[0]
        self.__parsed_content = inner_parser.div_data[max_divs]

    def get_title(self):
        self.wrapper.initial_indent = ""
        return self.wrapper.fill(self.__parsed_title)

    def get_article_body(self):
        text = ''
        self.wrapper.initial_indent = self.settings.get('article_indent')
        for paragraph in self.__parsed_content:
            text += self.wrapper.fill(paragraph)

        return text


class Article:
    def __init__(self, url):
        self.url = urlparse(url)
        self.title = ''
        self.content = ''

    def set_title(self, text):
        self.title = text

    def set_content(self, text):
        self.content = text

    def save(self, ext_file='txt'):
        filename = '{}{}.{}'.format(self.url.netloc, self.url.path[:-1], ext_file)
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, "w") as f:
            f.write(self.title + self.content)


class MainProgram:
    @staticmethod
    def run(url):
        settings = Settings()
        article = Article(url)

        response = ''
        try:
            with urllib.request.urlopen(url) as f:
                response = f.read().decode(f.headers.get_content_charset())
        except urllib.error.URLError as e:
            print('Something went wrong: ', e)
            exit()

        parser = Parser(response, settings)

        article.set_title(parser.get_title())
        article.set_content(parser.get_article_body())
        article.save(settings.get('ext_file'))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Scrapper news resources')
    parser.add_argument('url', type=str)
    args = parser.parse_args()
    MainProgram.run(args.url)
