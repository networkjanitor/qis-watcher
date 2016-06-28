import configparser
import os
import re
import sys
from html.parser import HTMLParser

import requests

_degree_list = []
_grade_list = []


class HTMLParserDegree(HTMLParser):
    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            for attr in attrs:
                if attr[0] == 'name':
                    _degree_list.append(attr[1])


class HTMLParserGrades(HTMLParser):
    count = 0
    dict = {}
    _data = ''
    _starttag = ''

    def __init__(self):
        super().__init__()
        self.count = 0
        self.dict = {}
        self._data = ''
        self._starttag = ''

    def handle_starttag(self, tag, attrs):
        self._starttag = ''

    def handle_data(self, data):
        self._data = data

    def handle_endtag(self, tag):
        # normal result:
        # sum of ects points result:
        if self.count == 0:
            self.dict['Fächercode'] = self._data.replace('\n', '').strip()
            self.count += 1
        elif self.count == 1:
            self.dict['Prüfungsleistung'] = self._data.replace('\n', '').strip()
            self.count += 1
        elif self.count == 2:
            self.dict['Art d. Prüf.'] = self._data.replace('\n', '').strip()
            self.count += 1
        elif self.count == 3:
            self.dict['Semester'] = self._data.replace('\n', '').strip()
            self.count += 1
        elif self.count == 4:
            self.dict['Note'] = self._data.replace('\n', '').strip()
            self.count += 1
        elif self.count == 5:
            self.dict['Versuch'] = self._data.replace('\n', '').strip()
            self.count += 1
        elif self.count == 6:
            self.dict['Prüfer'] = self._data.replace('\n', '').strip()
            self.count += 1
        elif self.count == 7:
            self.dict['Vermerk'] = self._data.replace('\n', '').strip()
            self.count += 1
        elif self.count == 8:
            self.dict['Freiversuch'] = self._data.replace('\n', '').strip()
            self.count += 1
        elif self.count == 9:
            self.dict['ECTS-Pkt'] = self._data.replace('\n', '').strip()
            _grade_list.append(self.dict)
        self._data = ''


def request_new_session():
    req = _Session.get('https://qis.fh-stralsund.de/qisserver/rds?state=user&type=0')
    with open('research/request_new_session.html', 'w') as f:
        f.write(req.text)
    if req.status_code == 200:
        return re.search('jsessionid=[^.]*', req.text).group(0)[11:]


def login_on_session(jsessionid, conf_file):
    payload = {'asdf': conf_file['account']['username'], 'fdsa': conf_file['account']['password'], 'submit': ' Ok '}
    req = _Session.get(
        'https://qis.fh-stralsund.de/qisserver/rds;jsessionid=' + jsessionid +
        '.kearney?state=user&type=1&category=auth.login&startpage=portal.vm',
        params=payload)
    with open('research/login_on_session.html', 'w') as f:
        f.write(req.text)
    if re.search('<span class=\"newSessionMsg nobr\">Anmeldung fehlgeschlagen</span>', req.text) is not None:
        raise RuntimeError('qis login failed')


def request_new_asi(jsessionid):
    req = _Session.get(
        'https://qis.fh-stralsund.de/qisserver/rds;jsessionid=' + jsessionid +
        '.kearney?state=change&type=1&moduleParameter=studyPOSMenu&nextdir=change&next=menu.vm&subdir=applications&'
        'xml=menu&purge=y&navigationPosition=functions%2CstudyPOSMenu&breadcrumb=studyPOSMenu&topitem=functions'
        '&subitem=studyPOSMenu')
    with open('research/request_new_asi.html', 'w') as f:
        f.write(req.text)
    if req.status_code == 200:
        return re.search('asi=[^"&]*', req.text).group(0)[4:]


def request_exams(jsessionid, asi):
    req = _Session.get('')
    with open('research/request_grades.html', 'w') as f:
        f.write(req.text)


def request_grades(jsessionid, asi):
    req = _Session.get(
        'https://qis.fh-stralsund.de/qisserver/rds;jsessionid=' + jsessionid + '.kearney?state=notenspiegelStudent&'
                                                                               'next=tree.vm&nextdir=qispos/notenspiegel/student&menuid=notenspiegelStudent&breadcrumb=notenspiegel&'
                                                                               'breadCrumbSource=menu&asi=' + asi)
    with open('research/request_exams_overview.html', 'w') as f:
        f.write(req.text)

    html = req.text
    html = html[html.find('<form METHOD="POST"'):html.find('</form>', html.find('<form METHOD="POST"'))]

    parser = HTMLParserDegree()
    parser.feed(html)

    grades = []

    for name in _degree_list:
        req = _Session.get(
            'https://qis.fh-stralsund.de/qisserver/rds;jsessionid=' + jsessionid + '.kearney?state=notenspiegelStudent&'
                                                                                   'next=list.vm&nextdir=qispos/notenspiegel/student&createInfos=Y&struct=auswahlBaum&expand=0&'
                                                                                   'nodeID=' + name + '&asi=' + asi)
        html = req.text
        html = html[html.find('<table border="0">'):html.rfind('</table>')]
        trs = html.split('</tr>')[2:]

        for tr in trs:
            t_tr = tr[tr.find('<tr>'):].replace('\t', '').replace('\n', '')
            parser = HTMLParserGrades()
            parser.feed(t_tr)
            grades.append(parser.dict.copy())
            parser.reset()

        grades = grades[:-1]  # Remove last empty object
        # Fix the misassigned mess for the ects sum
        ects_sum = grades[-1]
        ects_sum['ECTS-Pkt'] = ects_sum['Versuch']
        del (ects_sum['Prüfungsleistung'])
        del (ects_sum['Note'])
        del (ects_sum['Semester'])
        del (ects_sum['Versuch'])
    for grade in grades:
        print(grade)


def main():
    conf_file = configparser.ConfigParser()
    path_to_conf = os.path.abspath(os.path.dirname(sys.argv[0]))
    path_to_conf = os.path.join(path_to_conf, 'qis_watcher.conf')
    conf_file.read(path_to_conf)

    global _Session
    _Session = requests.Session()
    _Session.headers['user-agent'] = conf_file['requests']['useragent']
    try:
        jsessionid = request_new_session()
        login_on_session(jsessionid, conf_file)
        asi = request_new_asi(jsessionid)
        request_grades(jsessionid, asi)
    except Exception as e:
        with open('watcher.log', 'a') as f:
            f.write(str(e) + '\n')


if __name__ == '__main__':
    main()
