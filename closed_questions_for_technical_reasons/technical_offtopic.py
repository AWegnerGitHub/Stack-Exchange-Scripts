from __future__ import print_function
import logging
import json
import os.path
import operator
import user_settings
from prettytable import PrettyTable

import os, sys, inspect

currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)
from SEAPI import SEAPI

KEY = user_settings.API_KEY
ACCESS_TOKEN = user_settings.ACCESS_TOKEN


proxies = {}
try:
    M_SITE = SEAPI.SEAPI('hardwarerecs', key=KEY, proxy=proxies)
except SEAPI.SEAPIError as e:
    logging.critical("   Error URL: %s" % (e.url))
    logging.critical("   Error Number: %s" % (e.error))
    logging.critical("   Error Code: %s" % (e.code))
    logging.critical("   Error Message: %s" % (e.message))

M_SITE.page_size = 100
M_SITE.max_pages = 50


if os.path.isfile('technical_off_topc.json'):
    with open('technical_off_topc.json') as f:
        M_QUESTIONS = json.load(f)
else:
    M_QUESTIONS = M_SITE.fetch('/questions', filter='!*1SgQGDMkNmUs-Puy7G3rLIqve9zjwLyIG)5Zz.EL', order='desc', sort='creation')
    M_QUESTIONS = M_QUESTIONS['items']

    with open('technical_off_topc.json', 'w') as questions:
        json.dump(M_QUESTIONS, questions)

closed_count = 0
closed_technical = 0
for q in M_QUESTIONS:
    if 'closed_reason' in q and q['closed_reason'] == 'off-topic':
        closed_count += 1

    if 'closed_reason' in q and q['closed_reason'] == 'off-topic' and 'technical' in q['closed_details']['description'].lower():
        closed_technical += 1
        print(q['title'], q['link'])

print(closed_count)
print(closed_technical)