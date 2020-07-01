#!/usr/bin/env python3
from bs4 import BeautifulSoup
import request
import re
import os
import sys
from time import gmtime, strftime
from getpass import getpass  #password
import argparse

parser = argparse.ArgumentParser()

lunchtime = 40  #Minimum lunch time (minutes), used to calculate where the lunch is
lunchtoggle = True  #False if you don't want to print the lunch
english = False  #Language of the days

if english:
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
else:
    days = ['Måndag', 'Tisdag', 'Onsdag', 'Torsdag', 'Fredag', 'Lördag', 'Söndag']

parser.add_argument('--username', '-u', default='', help='SchoolSoft username')
parser.add_argument('--password', '-p', default='', help='SchoolSoft password')
parser.add_argument('--school', '-i', default='nacka', help='SchoolSoft school, if the URL is "sms13.schoolsoft.se/nacka/", the school name is "nacka"')
parser.add_argument('--ask', '-a', action='store_const', const=True, help='Asks for the password (if you don\'t want to store the password in the shell history)')

parser.add_argument('--schedule', '-s', default=[], choices=['0', '1', '2', '3', '4', 'today'], help='The days to get the schedule, use "today" to get current day')
parser.add_argument('--raw-schedule', '-rs', action='store_const', const=True, help='Print the raw schedule (useful for scripts)')
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
    import testkeys  #To import my own login details, you can remove this
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

    def __init__(self, school, username, password, usertype = 1):
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

    def try_get(self, url, attempts = 0):
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
                loginr = requests.post(self.login_page, data = {
                    "action": "login",
                    "usertype": self.usertype,
                    "ssusername": self.username,
                    "sspassword": self.password
                    }, cookies=self.cookies, allow_redirects=False)

                # Saves login cookie for faster access after first call
                self.cookies = loginr.cookies

                return self.try_get(url, attempts+1)
            else:
                raise AuthFailure("Invalid username or password")
        else:
            return r

    def fetch_lunch_menu(self, lunchweek = -1):
        """
        Fetches the lunch menu for the entire week
        Returns an ordered list with days going from index 0-4
        This list contains all the food on that day
        """
        menu_html = self.try_get("https://sms5.schoolsoft.se/{0}/jsp/student/right_student_lunchmenu.jsp?requestid={1}".format(self.school,lunchweek))
        menu = BeautifulSoup(menu_html.text, "html.parser")

        lunch_menu = []

        for div in menu.find_all("td", {"style": "word-wrap: break-word"}):
            food_info = div.get_text(separator=u"<br/>").split(u"<br/>")
            lunch_menu.append(food_info)
        if len(lunch_menu) == 0:
                if english:
                    return([['not available'],['not available'],['not available'],['not available'],['not available']])
                else:
                    return([['Inte tillgängligt'],['Inte tillgängligt'],['Inte tillgängligt'],['Inte tillgängligt'],['Inte tillgängligt']])
        else:
            return lunch_menu

    def fetch_schedule(self,scheduleweek=0):
        """
        Fetches the schedule of logged in user
        Returns an (not currently) ordered list with days going from index 0-4
        This list contains all events on that day
        """
        schedule_html = self.try_get("https://sms5.schoolsoft.se/{0}/jsp/student/right_student_schedule.jsp?requestid=-2&type=0&teacher=0&student=0&room=0&term={1}".format(self.school,scheduleweek))
        schedule = BeautifulSoup(schedule_html.text, "html.parser")
        full_schedule = []

        for a in schedule.find_all("a", {"class": "schedule"}):
            info = a.find("span")
            info_pretty = info.get_text(separator=u"<br/>").split(u"<br/>")
            full_schedule.append(info_pretty)

        return (full_schedule, str(schedule))
    
    def fetch_tests(self):
        tests = self.try_get("https://sms5.schoolsoft.se/{}/jsp/student/right_student_test_schedule.jsp?menu=test_schedule".format(self.school))
        tests = str(BeautifulSoup(tests.text, "html.parser"))
        return(tests)

api = SchoolSoft(school, username, password)  #__init__


lunch = api.fetch_lunch_menu(lunchweek)  #Sorted in an array
for a in range(5):  #This loop is to make sure there's always a veg option
    if len(lunch[a]) == 1:
        lunch[a].append(lunch[a][0])
schedule,full = api.fetch_schedule(scheduleweek)  #schedule
prov = api.fetch_tests()

#in order to get a list of all info on all days, every day has a col-5-days separator
mid = []
start = 0 
for a in range(prov.count('col-5-days')):
        start = prov[start:].find('col-5-days') + start + 1 
        stop = prov[start:].find('col-5-days') + start
        mid.append(prov[start:stop])

weekinfo = [ [],[]   ]
#weekinfo [0] = col-5-days number of the weekstart
#weekinfo [1] = weeknumber
tests = {
        "day":[],
        "label":[],
        "title":[],
        "week":[]
        } 
#tests["day"] = day of the test, starting from 0
#tests["label"] = label of the test, eg Test, Homework
#tests["title"] = Title of the test and more info
#tests["week"] = Week of the test
#example of a week with 2 tests
#[[0, 1], ['Prov', 'Prov'], ['Litteraturprov SVESVE02', 'Prov: psykodynamiskt perspektiv och beteendeperspektiv PSKPSY01'], [51, 51]]
for b in range(len(mid)):
        titleindex = 0
        labelindex = 0
        for a in range(mid[b].count('<label>')):  #multiple tests on the same day
            label = ((re.search('<label>[\W\w]*?<\/label>',mid[b][labelindex:]))).group(0).strip('<label>').strip('</label>')  #gets the label (Test, Homework, etc) 
            day = int(str(re.search('day=[0-6]',mid[b]).group(0)).strip('day='))  #day of the test
            tests["day"].append(day)
            tests["label"].append(label)
            tests["week"].append(round((b/6)-0.5)+weekinfo[1][0])
            if 'title="' in mid[b]: #gets the info on the test
                title = re.search('title="[\W\w\n]*?"',mid[b][titleindex:]).group(0).strip('title"').replace('\r\n">',' ')[2:-1] #Title can have max 50 characters, change regex if needed
                tests["title"].append(title)
            titleindex = mid[b][titleindex:].find('title="') + titleindex + 1 #Finds the location of the title
            labelindex = mid[b][labelindex:].find('<label>') + labelindex + 1
        if 'valign="top">v' in mid[b]:  #gets the week
            start = (mid[b]).find('valign="top"')+13 #could be done with regex, but this already works
            stop = (mid[b])[start:].find('<')+start
            week = int((mid[b])[start+1:stop])
            weekinfo[1].append(week)
            weekinfo[0].append(b)
    
    
full = full.replace('<td','\n') #Helps the cutter script
full = re.sub('class="schedulecell" rowspan="6" width="5%">[0-9]*[0-9]:[0-9][0-9]</td>','',full) #Replaces unwanted rowspans, important for the script to work

def Classes(full):
    start = 0
    groups = []
    for a in range(full.count('class="')):
        start = full[start:].find('class="') + start +1 
        group = re.search('class="[\W\w]*?"',full[start:])
        if group:
            group = group.group(0) #group as variable name may be confusing
    
        if group == 'class="schedulecell"':
            groups.append(1)
        if group == 'class="light schedulecell"':
            groups.append(0)
    groups = groups[6:] #Removes the first schedulecells which isn't part of the schedule
    return(groups)

groups = Classes(full)

def getRowspans(full):
    count = full.count('rowspan=') 
    begin = 0
    rowspans = []
    for a in range(count): #This for-loop finds all rowspans and appends them to rowspans[], useful for getting the schedule sorted
            start = full[begin:].find('rowspan')+begin+9
            rowspans.append(int(full[start:start+full[start:].find('"')]))
            begin =full[begin:].find('rowspan')+begin + 1
    return(rowspans)

#schedule_list["rowspans"] = rowspans (This isn't really needed for general use, just calculations)
#schedule_list["name"] = Class name 
#schedule_list["time"] = Class time
#schedule_list["location"] = Class location
#schedule_list["time2"] = Class time (formatted diffrently)
#schedule_list["type"] = Type of schedule (1 for class and 0 for break)
#Example:
#schedule_list["time"][3] = Class times on day 3 (Thursday) 
#schedule_list["name"][2][4] = Class name of the fifth class on day 2 (Wednesday)

def sortSchedule(full,schedule):
    rowspans = getRowspans(full)
    schedule_list = {
                    "rowspans":[ [],[],[],[],[] ],
                    "name"    :[ [],[],[],[],[] ],
                    "time"    :[ [],[],[],[],[] ],
                    "time2"   :[ [],[],[],[],[] ],      
                    "location":[ [],[],[],[],[] ],
                    "type"    :[ [],[],[],[],[] ]
                    }

    for a in range(len(rowspans)):
        summa = [ [],[],[],[],[]  ]
        for b in range(5):
            summa[b].append(sum(schedule_list["rowspans"][b]))
        schedule_list["rowspans"][summa.index(min(summa))].append(int(rowspans[a]))
        schedule_list["type"][summa.index(min(summa))].append(int(groups[a]))
        if groups[a]:  #If there's a class 
            schedule_list["name"][summa.index(min(summa))].append(schedule[0][0])
            schedule_list["time"][summa.index(min(summa))].append(schedule[0][1])
            schedule_list["location"][summa.index(min(summa))].append((schedule[0][2]).replace('\r\n',''))
            schedule.pop(0) #Removes the first item so the next item can be used, better than keeping count on what number you're on

    for c in range(5): #Time formatted diffrently, useful for other scripts
        for d in range(len(schedule_list["time"][c])):
            sep = schedule_list["time"][c][d].find('-')
            schedule_list["time2"][c].append(schedule_list["time"][c][d][:sep])
            schedule_list["time2"][c].append(schedule_list["time"][c][d][sep+1:])
            
    return(schedule_list)

schedule_list = sortSchedule(full,schedule)
if lunchtoggle:  #adds lunch to the schedule, based on break time
    for x in range(5):
        for y in range(len(schedule_list["type"][x])):
            if not schedule_list["type"][x][y] and y != 0 and int(schedule_list["rowspans"][x][y]) > (lunchtime/5):
                count = schedule_list["type"][x][:y].count(1) #Gets the amout of classes before lunch, for inserting lunch at the correct place
                schedule_list["name"][x].insert(count,'Lunch')
                schedule_list["time"][x].insert(count,'')
                schedule_list["location"][x].insert(count,'')
                schedule_list["time2"][x].insert(int(count*2),schedule_list["time2"][x][int(count*2)-1])
                schedule_list["time2"][x].insert(int(count*2)+1,schedule_list["time2"][x][int(count*2)+1])
                break #one lunch/day

lunchweek = args.lunchweek
scheduleweek = args.scheduleweek
day = args.schedule
prefix = args.discord

if args.lunch:
    for f in range(len(lunch)):
        print(lunch[f][0])
        if len(lunch[f]) > 1:
            print(lunch[f][1]+'\n')

if args.raw_schedule:
    print(schedule_list)
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
            if tests["week"][a] != tests["week"][a-1]:
                print(prefix+'Vecka: '+prefix+str(tests["week"][a]))
            print(prefix+days[tests["day"][a]]+prefix+'\n'+tests["label"][a]+': '+tests["title"][a])

for a in args.schedule:
    if a == 'today':
        day = (int(strftime("%w", gmtime()))-1)
    else:
        day = int(a)
    
    for e in range(len(schedule_list["name"][day])):
        print(schedule_list["name"][day][e],end='')  #end='' is to stop printing a new line
        if schedule_list["name"][day][e] == 'Lunch':
            print('')
        else:
            print(' ' + prefix + schedule_list["time"][day][e] + prefix + ' ', end='')
            print(schedule_list["location"][day][e])  #[:-2] to remove \n\r, remove this if it only partly prints classroom names
