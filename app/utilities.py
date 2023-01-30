#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re
import os
import sys
import shutil
import socket
import logging
import tldextract
from urllib.parse import urlparse

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

def nsresolve(fqdn):
    try:
        return socket.gethostbyname(fqdn)
    except socket.gaierror:
        return None

socksport = os.environ.get('SOCKS_PORT', 9050)
if nsresolve('host.docker.internal') is not None:
    socksaddr = os.environ.get('SOCKS_HOST', 'host.docker.internal')
else:
    socksaddr = os.environ.get('SOCKS_HOST', 'localhost')

file_checks = ['proxychains.conf', 'common/headers.txt']
path_checks = ['proxychains4','nmap']

def checktcp(host, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex((str(host), int(port)))
    sock.close()
    if result == 0:
        return True
    return False

def gen_chainconfig(socksaddr, socksport):
    if not checktcp(socksaddr, socksport):
        logging.critical('failed socks5 preflight socket check (%s:%s)', socksaddr, socksport)
        sys.exit(1)
    fqdnrex = re.compile(r'^[a-zA-Z0-9\-\.]+\.[a-zA-Z]{2,5}$')
    if fqdnrex.match(socksaddr):
        socksaddr = nsresolve(socksaddr)
    confstr = 'socks4 ' + socksaddr + ' ' + str(socksport)
    with open('proxychains.conf', 'r', encoding='utf-8') as chainconf:
        contents = chainconf.read()
        if 'socks4' not in contents:
            with open('proxychains.conf', 'a', encoding='utf-8') as chainconf:
                chainconf.write(confstr)
        else:
            logging.debug('socks4 already configured in proxychains.conf')

def getfqdn(url):
    url_object = tldextract.extract(url)
    if url_object.subdomain:
        return url_object.subdomain + '.' + url_object.domain + '.' + url_object.suffix
    return url_object.domain + '.' + url_object.suffix

def getbaseurl(url):
    urlparse_object = urlparse(url)
    if urlparse_object.path == '':
        return url
    return urlparse_object.scheme + '://' + urlparse_object.netloc

def getsocks():
    if not checktcp(socksaddr, socksport):
        logging.critical('failed socks5 preflight socket check (%s:%s)', socksaddr, socksport)
        sys.exit(1)
    oproxies = {
        'http':  'socks5h://' + socksaddr + ':' + str(socksport),
        'https': 'socks5h://' + socksaddr + ':' + str(socksport)
    }
    return oproxies

def preflight():
    for path_item in path_checks:
        check = shutil.which(path_item)
        if check is None:
            logging.critical('%f not found in path', path_item)
            sys.exit(1)
    for file in file_checks:
        if not os.path.isfile(file):
            logging.critical('%f not found', file)
            sys.exit(1)
