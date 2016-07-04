import argparse
import json
from textwrap import TextWrapper
from urllib.parse import urlparse

import os
import requests
from bs4 import BeautifulSoup


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


class Parser:
    """
    Основной разбор происходит в этом классе, при создании экземпляра класса
    так же задаются настройки, как глобальные так и для обрабатываемого хоста.
    По алгоритму каждая статья должна иметь тег заголовка, для более точного
    определения так же указывается класс или иной атрибут заголовка, затем
    происходит разбор содержания статьи, опять же как правило статья находится
    в окружающем теге с определенным классом, мы задаем этот элемент в настройках,
    а так же задаем атрибут, чтобы можно было точнее определить элемент и
    пробегаем по дочерним элементам, параграфам статьи, собираем в одну переменную
    и отдаем при вызове функции.
    Для работы обязательно нужно задать настройки для домена
    """
    def __init__(self, raw_data, settings, host_settings):
        self.page = BeautifulSoup(raw_data, "html.parser")
        self.settings = settings
        self.host_settings = host_settings
        self.wrapper = TextWrapper(width=self.settings.get('text_width'))

    def get_title(self):
        self.wrapper.initial_indent = ""
        return self.wrapper.fill(self.page.find(self.host_settings['header_elem'],
                                                self.host_settings['header_attrs']).get_text())

    def get_article_body(self):
        text = ''
        self.wrapper.initial_indent = self.settings.get('article_indent')
        for paragraph in self.page \
                .find(self.host_settings['article_elem'], self.host_settings['article_attrs']) \
                .find_all(self.host_settings['sub_article_elem']):
            for link in paragraph.find_all('a'):
                link.replace_with('{}[{}]'.format(link.get_text(), link['href']))
            text += self.wrapper.fill(paragraph.text.strip())

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
        host_settings = settings.get(article.url.netloc)
        if not host_settings:
            raise TypeError('Settings for current host not found')

        response = requests.get(url)
        parser = Parser(response.text, settings, host_settings)

        article.set_title(parser.get_title())
        article.set_content(parser.get_article_body())
        article.save(settings.get('ext_file'))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Scrapper news resources')
    parser.add_argument('url', type=str)
    args = parser.parse_args()
    MainProgram.run(args.url)
