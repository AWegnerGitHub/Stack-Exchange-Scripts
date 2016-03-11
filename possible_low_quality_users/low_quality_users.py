from __future__ import print_function
import logging
import json
import os.path
import operator
import user_settings
from prettytable import PrettyTable
from time import sleep
import datetime
from collections import deque
from operator import index, attrgetter
from difflib import SequenceMatcher
import itertools

import os, sys, inspect

currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)
from SEAPI import SEAPI
from utils import utils

KEY = user_settings.API_KEY
ACCESS_TOKEN = user_settings.ACCESS_TOKEN
REPUTATION_THRESHOLD = 50
ANSWER_FILTER = '!FcbKfKGCs3WA2*zYQls9tTyGQ5'
SIMILARITY_THRESHOLD = 0.80
NUM_SHORT_ANSWERS_THRESHOLD = 3
SHORT_ANSWER_LENGTH_THRESHOLD = 75
MAX_QUEUE_SIZE = 250
BATCH_MINUTES = 30
BATCH_THRESHOLD = 4
MINUTES_THRESHOLD = 2

logging = utils.setup_logging("low_quality", file_level=logging.INFO, console_level=logging.INFO,
                                requests_level=logging.CRITICAL)

# TODO:
#   Things to check:
#       Answer similarity
#       Link similarity (domain and exact links)
#       Multiple short answers
#   Smaller queue?


class User(object):
    """Class of users that have been seen"""
    def __init__(self, id, name, link, reputation):
        self.id = id
        self.name = name
        self.link = link
        self.reputation = reputation
        self.answers = set()
        self.similar_answers = set()
        self.short_answers = set()
        self.questions = set()
        self.comments = set()

    def __eq__(self, item):
        """A Users is equal to a User if the ids match"""
        if isinstance(item, User):
            return self.id == item.id
        try:
            return self.id == index(item)
        except TypeError:
            return NotImplemented

    def __ne__(self, item):
        ret = self == item
        if ret is NotImplemented:
            return ret
        return not ret

    def __hash__(self):
        return self.id

    def __repr__(self):
        try:
            return "{} - {} - {} - {}  Answers: {}, Questions: {}, Comments: {}".format(self.id, self.name,
                                                                                    self.reputation, self.link,
                                                                                    self.answers, self.questions,
                                                                                    self.comments)
        except UnicodeEncodeError:
            return "{} - {} - {}  Answers: {}, Questions: {}, Comments: {}".format(self.id,
                                                                                    self.reputation, self.link,
                                                                                    self.answers, self.questions,
                                                                                    self.comments)

proxies = {}
try:
    M_SITE = SEAPI.SEAPI('stackoverflow', key=KEY, proxy=proxies)
except SEAPI.SEAPIError as e:
    logging.critical("   Error URL: %s" % (e.url))
    logging.critical("   Error Number: %s" % (e.error))
    logging.critical("   Error Code: %s" % (e.code))
    logging.critical("   Error Message: %s" % (e.message))

M_SITE.page_size = 100
M_SITE.max_pages = 5

other_settings = None

def get_timestamps():
    epoch = datetime.datetime(1970,1,1)
    now_ts = (datetime.datetime.utcnow() - epoch).total_seconds()
    try:
        previous_run_ts = (datetime.datetime.strptime(other_settings['lastrun'],"%Y-%m-%dT%H:%M:%S.%f") - epoch).total_seconds()
    except TypeError:
        previous_run_ts = (other_settings['lastrun'] - epoch).total_seconds()
    return int(now_ts), int(previous_run_ts)

def update_settings():
    other_settings['lastrun'] = datetime.datetime.utcnow()
    save_settings()

def save_settings():
    with open('other_settings.json', 'w') as users:
        json.dump(other_settings, users, default=json_serial)

def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, datetime.datetime):
        serial = obj.isoformat()
        return serial
    raise TypeError ("Type not serializable")

def compare(a, b):
    """Use the SequenceMatcher to return the similarity ratio"""
    return SequenceMatcher(None, a, b).ratio()

def check_similar(user):
    """Checks a user's posts for similarity to their other recent posts"""
    # Check answers first
    similar_answers = False
    if len(user.answers) > 1:
        # Compare using SequenceMatcher (if this gets to slow, try using Levenshtein instead)
        for a, a1 in itertools.combinations(user.answers, 2):
            similarity = compare(a[2], a1[2])
            if similarity > SIMILARITY_THRESHOLD:
                user.similar_answers.add((a, a1))
                similar_answers = True

    return user, similar_answers


def check_short_answers(user):
    short_answers = False
    if len(user.answers) > 1:
        for a in user.answers:
            if len(a[2]) <= SHORT_ANSWER_LENGTH_THRESHOLD:
                user.short_answers.add(a)
        if len(user.short_answers) >= NUM_SHORT_ANSWERS_THRESHOLD:
            short_answers = True

    return user, short_answers

if os.path.isfile('other_settings.json'):
    with open('other_settings.json') as f:
        other_settings = json.load(f)
else:
    other_settings = {
        'lastrun': datetime.datetime.utcnow()
    }

    save_settings()

watched_users = deque(maxlen=MAX_QUEUE_SIZE)

### We are going to abuse the deque a bit and allow removal of items in the middle and then reinsert the item at the end
### This is to keep Users that keep popping up in the queue, but others can drop out over time

while True:
    now, previous = get_timestamps()
    now_readable = datetime.datetime.fromtimestamp(now).strftime('%Y-%m-%d %H:%M:%S.%f')
    previous_readable = datetime.datetime.fromtimestamp(previous).strftime('%Y-%m-%d %H:%M:%S.%f')
    logging.info("Retrieving answers created between {} and {}".format(previous_readable, now_readable))
    try:
        ANSWERS = M_SITE.fetch('answers', filter=ANSWER_FILTER, order='desc', sort='creation', fromdate=previous, todate=now)
    except SEAPI.SEAPIError as e:
        logging.critical("   Error URL: %s" % (e.url))
        logging.critical("   Error Number: %s" % (e.error))
        logging.critical("   Error Code: %s" % (e.code))
        logging.critical("   Error Message: %s" % (e.message))
        continue
    ANSWERS = ANSWERS['items']
    added_this_batch = []
    for a in ANSWERS:
        if a['owner']['user_id'] not in watched_users:
            if a['owner']['reputation'] < REPUTATION_THRESHOLD:
                user = User(id=a['owner']['user_id'], name=a['owner']['display_name'], link=a['owner']['link'], reputation=a['owner']['reputation'])
                user.answers.add((a['answer_id'], a['link'], a['body']))
                watched_users.append(user)
                added_this_batch.append(a['owner']['user_id'])
        else:
            for u in watched_users:
                if a['owner']['user_id'] == u:
                    u.answers.add((a['answer_id'], a['link'], a['body']))
                    added_this_batch.append(a['owner']['user_id'])

    added_this_batch = set(added_this_batch)
    for u in watched_users:
        if u.id in added_this_batch:
            u, is_similar_answer = check_similar(u)
            u, is_multiple_short_answers = check_short_answers(u)
            if is_similar_answer or is_multiple_short_answers:       # Other conditions go here
                logging.info("    User: {}".format(u.id))
                for a in u.similar_answers:
                    logging.info("        Similar Answers: {} => {}".format(a[0][1], a[1][1]))
                for a in u.short_answers:
                    logging.info("        Short Answer: {}".format(a[1]))

    update_settings()
    logging.debug("Size of queue: {}".format(len(watched_users)))
    sleep(600)



