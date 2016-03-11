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
M_SITE.max_pages = 5

M_USERS = M_SITE.fetch('/users', filter='!.L9MciaPYVrEUY9WxiuyZdlo.Yt5H', order='desc', sort='reputation')
M_USERS = M_USERS['items']

sorted_downvotes = sorted(M_USERS, key=lambda k: k['down_vote_count'], reverse=True)
sorted_upvotes = sorted(M_USERS, key=lambda k: k['up_vote_count'], reverse=True)

table = PrettyTable(["Count", "Name", "Downvotes"])
print("---Downvotes---")
count = 1
for user in sorted_downvotes:
    if user['down_vote_count'] > 0:
        table.add_row([count, user['display_name'], user['down_vote_count']])
        count += 1
    else:
        break

print(table)

table = PrettyTable(["Count", "Name", "Upvotes"])
print("---Upvotes---")
count = 1
for user in sorted_upvotes:
    if user['up_vote_count'] > 0:
        table.add_row([count, user['display_name'], user['up_vote_count']])
        count += 1
    else:
        break

print(table)

