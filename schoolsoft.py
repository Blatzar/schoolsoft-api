#!/usr/bin/env python3
from bs4 import BeautifulSoup
import requests
import re
import os
import sys
from time import gmtime, strftime
from getpass import getpass  # password
import argparse

parser = argparse.ArgumentParser()

lunchtime = 40  # Minimum lunch time (minutes), used to calculate where the lunch is
lunchtoggle = True  # False if you don't want to print the lunch
english = False  # Language of the days

if english:
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
else:
    days = ['Måndag', 'Tisdag', 'Onsdag', 'Torsdag', 'Fredag', 'Lördag', 'Söndag']

parser.add_argument('--username', '-u', default='', help='SchoolSoft username')
parser.add_argument('--password', '-p', default='', help='SchoolSoft password')
parser.add_argument('--school', '-i', default='nacka', help='SchoolSoft school, if the URL is "sms13.schoolsoft.se/nacka/", the school name is "nacka"')
parser.add_argument('--ask', '-a', action='store_const', const=True, help='Asks for the password (if you don\'t want to store the password in the shell history)')

parser.add_argument('--schedule', '-s', default=[], choices=['0', '1', '2', '3', '4', 'today'], help='The days to get the schedule, use "today" to get current day')
# parser.add_argument('--raw-schedule', '-rs', action='store_const', const=True, help='Print the raw schedule (useful for scripts)')
parser.add_argument('--scheduleweek', '-sw', default=0, help='Specify the week to get the schedule (default: current week)')

parser.add_argument('--lunch', '-l', action='store_const', const=True, help='Print the lunch')
parser.add_argument('--raw-lunch', '-rl', action='store_const', const=True, help='Print the raw lunch (useful for scripts)')
parser.add_argument('--lunchweek', '-lw', default=-1, help='Specify the week to get the lunch (default: current week)')

parser.add_argument('--tests', '-t', action='store_const', const=True, help='Print the tests')
parser.add_argument('--discord', '-d', action='store_const', const="**", default="", help='Use discord formatting (useful for discord bots)')
args = parser.parse_args()

username = args.username
password = args.password
school = args.school
lunchweek = args.lunchweek
scheduleweek = args.scheduleweek

try:
    import testkeys  # To import my own login details, you can remove this
    testkeys = testkeys.school()
    school = testkeys.school
    username = testkeys.username
    password = testkeys.password
except ImportError:
    pass


if args.ask:
    password = getpass()


class AuthFailure(Exception):
    """In case API authentication fails"""
    pass


class SchoolSoft(object):
    """SchoolSoft Core API (Unofficial)"""

    def __init__(self, school, username, password, usertype=1):
        """
        school = School being accessed
        username = Username of account being logged in
        password = Password of account being logged in
        usertype = Type of account;
        0 = teacher, 1 = student
        """
        self.school = school

        self.username = username
        self.password = password
        self.usertype = usertype

        self.cookies = {}

        _login_page_re = r"https://sms(\d*).schoolsoft.se/%s/html/redirect_login.htm"
        self._login_page_re = re.compile(_login_page_re % school)

        # Might not be needed, still gonna leave it here
        self.login_page = "https://sms5.schoolsoft.se/{}/jsp/Login.jsp".format(school)

    def try_get(self, url, attempts=0):
        """
        Tries to get URL info using
        self.username && self.password

        Mainly for internal calling;
        however can be used to fetch from pages not yet added to API.
        """
        r = requests.get(url, cookies=self.cookies)

        login_page_match = self._login_page_re.match(r.url)
        if login_page_match:
            server_n = login_page_match.groups()
            if attempts < 1:
                # Sends a post request with self.username && self.password
                loginr = requests.post(self.login_page, data={
                    "action": "login",
                    "usertype": self.usertype,
                    "ssusername": self.username,
                    "sspassword": self.password
                }, cookies=self.cookies, allow_redirects=False)

                # Saves login cookie for faster access after first call
                self.cookies = loginr.cookies

                return self.try_get(url, attempts + 1)
            else:
                raise AuthFailure("Invalid username or password")
        else:
            return r

    def fetch_lunch_menu(self, lunchweek: int = None) -> list:
        """
        Fetches the lunch menu for the entire week
        Returns an ordered list with days going from index 0-4
        This list contains all the food on that day
        """
        if lunchweek is None:
            lunchweek = -1

        menu_html = self.try_get("https://sms5.schoolsoft.se/{0}/jsp/student/right_student_lunchmenu.jsp?requestid={1}".format(self.school, lunchweek))
        menu = BeautifulSoup(menu_html.text, "html.parser")

        lunch_menu = []

        for div in menu.find_all("td", {"style": "word-wrap: break-word"}):
            food_info = div.get_text(separator=u"<br/>").split(u"<br/>")
            lunch_menu.append(food_info)

        return lunch_menu

    def sort_schedule(self, schedule_bs4) -> list:

        class Day(object):
            def __init__(self, number, max_colspan):
                self.max_colspan = max_colspan
                self.number = number
                self.schedule = []
                self.colspan = 0
                self.lesson_colspan = 0
                self.small_rowspans = [0] * max_colspan

        class Block(object):
            def __init__(self, element, offset, is_break):

                self.element = element
                self.offset = offset
                self.is_break = is_break

                # TODO fix placehodlers.
                if not self.is_break:
                    info_pretty = element.get_text(separator="<br/>").split("<br/>")
                    self.subject = info_pretty[0]
                    self.subject_2 = info_pretty[3]
                    self.time = info_pretty[1]
                    self.location = info_pretty[2]

        days = []
        rows = schedule_bs4.select("tr.background.schedulerow")

        for rowspans, row in enumerate(rows):
            # Every rowspan is 5 minutes.
            elements = row.select("td.schedulecell")

            time_regex = r"^(1|2|)\d:[0-6]\d$"
            # Removes unwanted time cells (e.g 9:30)
            elements = [element for element in elements if not re.match(time_regex, element.text)]

            for element_no, element in enumerate(elements):
                # The time schedulecell doesn't have colspan.
                if element.get("colspan"):
                    is_break = 'light' in element.attrs["class"]

                    colspan = int(element["colspan"])
                    rowspan = int(element.get("rowspan", 0))

                    # The first cells are always days.
                    if rowspans == 0:
                        days.append(Day(element_no, colspan))
                    else:
                        day = sorted(days, key=lambda Day: min(Day.small_rowspans))[0]
                        indx = day.small_rowspans.index(min(day.small_rowspans))
                        day.schedule.append(Block(element, day.small_rowspans[indx], is_break))

                        for num, small_rowspan in enumerate(day.small_rowspans[indx:indx + colspan]):
                            day.small_rowspans[indx + num] += rowspan

                        day.colspan += int(element["colspan"])

                        if not is_break:
                            day.lesson_colspan += int(element["colspan"])

                        if day.lesson_colspan >= day.max_colspan:
                            day.colspan = 0
                            day.lesson_colspan = 0

                        if day.colspan >= day.max_colspan:
                            day.colspan = 0
        return days

    def fetch_schedule(self, scheduleweek: int = 0, requestid: int = None) -> list:
        """
        Fetches the schedule of logged in user
        Returns an (not currently) ordered list with days going from index 0-4
        This list contains all events on that day
        """
        if requestid is None:
            requestid = "-2"

        schedule_url = f"https://sms5.schoolsoft.se/{self.school}/jsp/student/right_student_schedule.jsp?requestid={requestid}&term={scheduleweek}"
        schedule_html = self.try_get(schedule_url)
        schedule_bs4 = BeautifulSoup(schedule_html.text, "html.parser")

        sorted_schedule = self.sort_schedule(schedule_bs4)
        return sorted_schedule

    def fetch_tests(self):
        tests = self.try_get("https://sms5.schoolsoft.se/{}/jsp/student/right_student_test_schedule.jsp?menu=test_schedule".format(self.school))
        tests = str(BeautifulSoup(tests.text, "html.parser"))
        return tests


api = SchoolSoft(school, username, password)  # __init__

lunch = api.fetch_lunch_menu(lunchweek)  # Sorted in an array

schedule = api.fetch_schedule(scheduleweek)  # schedule

prov = api.fetch_tests()

# in order to get a list of all info on all days, every day has a col-5-days separator
mid = []
start = 0
for a in range(prov.count('col-5-days')):
    start = prov[start:].find('col-5-days') + start + 1
    stop = prov[start:].find('col-5-days') + start
    mid.append(prov[start:stop])


weekinfo = [[], []]
# weekinfo [0] = col-5-days number of the weekstart
#weekinfo [1] = weeknumber
tests = {
    "day": [],
    "label": [],
    "title": [],
    "week": []
}
# tests["day"] = day of the test, starting from 0
# tests["label"] = label of the test, eg Test, Homework
# tests["title"] = Title of the test and more info
# tests["week"] = Week of the test
# example of a week with 2 tests
#[[0, 1], ['Prov', 'Prov'], ['Litteraturprov SVESVE02', 'Prov: psykodynamiskt perspektiv och beteendeperspektiv PSKPSY01'], [51, 51]]
for b in range(len(mid)):
    titleindex = 0
    labelindex = 0
    for a in range(mid[b].count('<label>')):  # multiple tests on the same day
        label = ((re.search(r'<label>[\W\w]*?<\/label>', mid[b][labelindex:]))).group(0).strip('<label>').strip('</label>')  # gets the label (Test, Homework, etc)
        day = int(str(re.search('day=[0-6]', mid[b]).group(0)).strip('day='))  # day of the test
        tests["day"].append(day)
        tests["label"].append(label)
        tests["week"].append(round((b / 6) - 0.5) + weekinfo[1][0])
        if 'title="' in mid[b]:  # gets the info on the test
            title = re.search(r'title="[\W\w\n]*?"', mid[b][titleindex:]).group(0).strip('title"').replace('\r\n">', ' ')[2:-1]  # Title can have max 50 characters, change regex if needed
            tests["title"].append(title)
        titleindex = mid[b][titleindex:].find('title="') + titleindex + 1  # Finds the location of the title
        labelindex = mid[b][labelindex:].find('<label>') + labelindex + 1
    if 'valign="top">v' in mid[b]:  # gets the week
        start = (mid[b]).find('valign="top"') + 13  # could be done with regex, but this already works
        stop = (mid[b])[start:].find('<') + start
        week = int((mid[b])[start + 1:stop])
        weekinfo[1].append(week)
        weekinfo[0].append(b)


if lunchtoggle:  # adds lunch to the schedule, based on break time
    for day in schedule:
        for block in day.schedule:
            if block.is_break and int(block.element["rowspan"]) > (lunchtime / 5):
                block.is_break = False
                block.subject = "Lunch"
                block.time = ""
                block.location = ""
                break

lunchweek = args.lunchweek
scheduleweek = args.scheduleweek
day = args.schedule
prefix = args.discord

if args.lunch:
    for f in range(len(lunch)):
        print(lunch[f][0])
        if len(lunch[f]) > 1:
            print(lunch[f][1] + '\n')

if args.raw_lunch:
    print(lunch)

if args.tests:
    if len(tests["day"]) == 0:
        if english:
            print('No tests upcoming')
        else:
            print('Inga prov eller läxor')
    else:
        for a in range(len(tests["day"])):
            if tests["week"][a] != tests["week"][a - 1]:
                print(prefix + 'Vecka: ' + prefix + str(tests["week"][a]))
            print(prefix + days[tests["day"][a]] + prefix + '\n' + tests["label"][a] + ': ' + tests["title"][a])

for arg in args.schedule:
    if arg == 'today':
        day = (int(strftime("%w", gmtime())) - 1)
    else:
        day = int(arg)

    for block in schedule[day].schedule:
        if not block.is_break:
            print(f"{block.subject} {block.time} {block.location}")
