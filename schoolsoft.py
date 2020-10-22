#!/usr/bin/env python3
from bs4 import BeautifulSoup
import requests
import re
import os
from time import gmtime, strftime
from getpass import getpass  # password
import argparse


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
            """
            Day object in schedule.
            max_colspan = maximum width a day can have, used to calculate if a day is full horizontally
            number = daynumber, starting from 0
            schedule = list of schedule elements as Block Objects
            colspan = current colspan "used", including breaks. Only used for calculations.
            lesson_colspan = same as colspan, but not counting breaks. Only used for calculations.
            small_rowspans = a list of rowspans used to track time. Only used for calculations.
            """
            def __init__(self, number, max_colspan):
                self.max_colspan = max_colspan
                self.number = number
                self.schedule = []
                self.colspan = 0
                self.lesson_colspan = 0
                self.small_rowspans = [0] * max_colspan

        class Block(object):
            """
            Block object for each lesson.
            element = bs4 element
            offset = rowspans since start, can be used to calculate time.
                     e.g if the schedule starts on 8:00 and the offset is 4 the
                     lesson start time is 8:00 + 4*5 minutes = 8:20. Each rowspan is 5 minutes.

            """
            def __init__(self, element, offset, is_break):
                self.element = element
                self.offset = offset
                self.is_break = is_break

                # TODO fix placehodlers.
                if not self.is_break:
                    info_pretty = element.get_text(separator="<br/>").split("<br/>")
                    self.subject = info_pretty[0]
                    self.time = info_pretty[1]

                    # Edgecase when there's no location.
                    if len(info_pretty) == 3:
                        self.location = None
                        self.group = info_pretty[2]
                    else:
                        self.group = info_pretty[3]
                        self.location = info_pretty[2]
                else:
                    self.subject = None
                    self.time = None
                    self.location = None
                    self.group = None

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
                        days.append(Day(element_no - 1, colspan))
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

    def fetch_schedule(self, scheduleweek: int = 0, requestid: int = None, lunchtoggle: bool = False, lunchtime: int = 40) -> list:
        """
        Fetches the schedule of logged in user
        Returns an (not currently) ordered list with days going from index 0-4
        This list contains all events on that day
        """
        if requestid is None:
            # Personal schedule.
            requestid = -2

        schedule_url = f"https://sms5.schoolsoft.se/{self.school}/jsp/student/right_student_schedule.jsp?requestid={requestid}&term={scheduleweek}"
        schedule_html = self.try_get(schedule_url)
        schedule_bs4 = BeautifulSoup(schedule_html.text, "html.parser")

        sorted_schedule = self.sort_schedule(schedule_bs4)

        if lunchtoggle:  # adds lunch to the schedule, based on break time
            for day in sorted_schedule:
                for block in day.schedule:
                    if block.is_break and int(block.element["rowspan"]) > (lunchtime / 5):
                        block.is_break = False
                        block.subject = "Lunch"
                        block.time = ""
                        block.location = ""
                        break

        return sorted_schedule

    def sort_tests(self, tests):
        class Test(object):
            def __init__(self, element):
                self.element = element
                self.label = self.element.find("label").text
                self.title = self.element.find("a")["title"]
                self.subject = self.element.find("a").text

        test_dict = {}
        rows = tests.select("table.table.table-striped.table-condensed > tr")
        for row in rows:
            cells = row.select("td.col-5-days")
            if cells:
                weeknum = int(re.search(r"\d+", cells[0].text).group())
                test_dict[weeknum] = [[], [], [], [], []]
                for day, cell in enumerate(cells[1:]):
                    for test in cell.select("div"):
                        test_dict[weeknum][day].append(Test(test))
        return test_dict

    def fetch_tests(self):
        tests = self.try_get("https://sms5.schoolsoft.se/{}/jsp/student/right_student_test_schedule.jsp?menu=test_schedule".format(self.school))
        tests = BeautifulSoup(tests.text, "html.parser")
        fixed_tests = self.sort_tests(tests)
        return fixed_tests


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    lunchtime = 40  # Minimum lunch time (minutes), used to calculate where the lunch is
    lunchtoggle = True  # False if you don't want to print the lunch

    day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

    parser.add_argument('--username', '-u', default='', help='SchoolSoft username')
    parser.add_argument('--password', '-p', default='', help='SchoolSoft password')
    parser.add_argument('--school', '-i', default='nacka', help='SchoolSoft school, if the URL is "sms13.schoolsoft.se/nacka/", the school name is "nacka"')
    parser.add_argument('--ask', '-a', action='store_const', const=True, help='Asks for the password (if you don\'t want to store the password in the shell history)')

    parser.add_argument('--schedule', '-s', default=[], choices=['0', '1', '2', '3', '4', 'today'], help='The days to get the schedule, use "today" to get current day')
    # parser.add_argument('--raw-schedule', '-rs', action='store_const', const=True, help='Print the raw schedule (useful for scripts)')
    parser.add_argument('--schedule-week', '-sw', default=0, type=int, help='Specify the week to get the schedule (default: current week)')
    parser.add_argument('--schedule-id', '-id', default=None, type=int, help='Specify the ID used to get the schedule (default: personal schedule)')

    parser.add_argument('--lunch', '-l', action='store_const', const=True, help='Print the lunch')
    # parser.add_argument('--raw-lunch', '-rl', action='store_const', const=True, help='Print the raw lunch (useful for scripts)')
    parser.add_argument('--lunchweek', '-lw', default=-1, help='Specify the week to get the lunch (default: current week)')

    parser.add_argument('--tests', '-t', action='store_const', const=True, help='Print the tests')

    args = parser.parse_args()

    username = args.username
    password = args.password
    school = args.school
    lunchweek = args.lunchweek
    scheduleweek = args.schedule_week
    day = args.schedule
    request_id = args.schedule_id

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

    api = SchoolSoft(school, username, password)  # __init__

    if args.lunch:
        lunch = api.fetch_lunch_menu(lunchweek)  # Sorted in an array
        for f in range(len(lunch)):
            print(lunch[f][0])
            if len(lunch[f]) > 1:
                print(lunch[f][1] + '\n')

    if args.tests:
        tests = api.fetch_tests()
        for weeknum, week in tests.items():
            print('-' * 10)
            print(f"{weeknum}: ")
            for day_number, day in enumerate(week):
                for test in day:
                    print(f"{day_names[day_number]} {test.label} {test.subject}")
        print('-' * 10)

    for arg in args.schedule:
        schedule = api.fetch_schedule(scheduleweek, requestid=request_id, lunchtoggle=lunchtoggle, lunchtime=lunchtime)  # schedule
        if arg == 'today':
            day = (int(strftime("%w", gmtime())) - 1)
        else:
            day = int(arg)

        for block in schedule[day].schedule:
            if not block.is_break:
                print(f"{block.subject} {block.time} {block.location.strip()}")
