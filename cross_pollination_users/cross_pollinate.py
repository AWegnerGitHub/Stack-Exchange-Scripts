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
MONITOR_SITE = "Hardware Recommendations"
CROSS_SITE = "Software Recommendations"

proxies = {}


def chunks(l, n):
    """Yield successive n-sized chunks from l."""
    for i in xrange(0, len(l), n):
        yield l[i:i + n]


if os.path.isfile('users.json'):
    with open('users.json') as f:
        M_USERS = json.load(f)
else:
    try:
        M_SITE = SEAPI.SEAPI('hardwarerecs', key=KEY, proxy=proxies)
    except SEAPI.SEAPIError as e:
        logging.critical("   Error URL: %s" % (e.url))
        logging.critical("   Error Number: %s" % (e.error))
        logging.critical("   Error Code: %s" % (e.code))
        logging.critical("   Error Message: %s" % (e.message))

    M_SITE.page_size = 100
    M_SITE.max_pages = 5

    M_USERS = M_SITE.fetch('/users', filter='!G*klMr_B6_t3PwaYs.S9VT(2y4', order='desc', sort='reputation')
    with open('users.json', 'w') as users:
        json.dump(M_USERS, users)

check_users = []
for user in M_USERS['items']:
    if user['reputation'] != 1 and user['reputation'] != 101:
        check_users.append(user)

print("There are {} users with reputation not equal to 1 or 101 (out of a total {} (or more) users)".format(
    len(check_users), len(M_USERS['items'])))

if os.path.isfile('users_on_both.json'):
    with open('users_on_both.json') as f:
        users_on_both = json.load(f)
else:
    users_on_both = []
    for users in list(chunks(check_users, 100)):
        user_ids = []
        for user in users:
            user_ids.append(user['account_id'])

        try:
            SITE = SEAPI.SEAPI('softwarerecs', key=KEY, proxy=proxies)
            SITE._api_key = None  # The /users/%s/associated end point doesn't belong to a site, so we have to remove the key, yet keep the SEAPI object
        except SEAPI.SEAPIError as e:
            logging.critical("   Error URL: %s" % (e.url))
            logging.critical("   Error Number: %s" % (e.error))
            logging.critical("   Error Code: %s" % (e.code))
            logging.critical("   Error Message: %s" % (e.message))
        SITE.page_size = 100
        SITE.max_pages = 250

        ids = ';'.join(str(x) for x in user_ids)
        try:
            associated_users = SITE.fetch('/users/%s/associated' % (ids), filter='!SlS8esjm8VBL-)Dl8j')
        except SEAPI.SEAPIError as e:
            logging.critical("   Error URL: %s" % (e.url))
            logging.critical("   Error Number: %s" % (e.error))
            logging.critical("   Error Code: %s" % (e.code))
            logging.critical("   Error Message: %s" % (e.message))
        for a_user in associated_users['items']:
            if CROSS_SITE in a_user['site_name']:
                users_on_both.append(a_user)

    with open('users_on_both.json', 'w') as users:
        json.dump(users_on_both, users)

sorting_key = operator.itemgetter("account_id")
a = sorted(users_on_both, key=sorting_key)
b = sorted(M_USERS['items'], key=sorting_key)

unique_both = {v['account_id']: v for v in users_on_both}.values()

merged = []
for user in unique_both:
    for m_user in check_users:
        if user['account_id'] == m_user['account_id']:
            merged.append({
                'account_id': m_user['account_id'],
                'rep_here': m_user['reputation'],
                'rep_there': user['reputation'],
                'link': m_user['link'],
                'name': m_user['display_name']
            }
            )

sorted_merge = sorted(merged, key=lambda k: k['rep_here'], reverse=True)
table = PrettyTable(["Name", "HR Rep", "SR Rep", "Account ID", "Link"])
for user in sorted_merge:
    if user['rep_there'] != 1 and user['rep_there'] != 101:
        table.add_row([user['name'], user['rep_here'], user['rep_there'], user['account_id'], user['link']])

print(table)
