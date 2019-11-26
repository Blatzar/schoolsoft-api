#!/usr/bin/env python3
from bs4 import BeautifulSoup
import requests
import re
import os
import sys

username = ''
password = ''
school = 'nacka' #if your schoolsoft-url is "https://sms13.schoolsoft.se/nacka/" then the schoolname is "nacka"

for a in range(len(sys.argv)):
    if sys.argv[a] == '--ask':
        password = input('Input the password now\n')
        os.system('clear')
    if sys.argv[a] == '--password':
        password = sys.argv[a+1]
    if sys.argv[a] == '--username':
        username = sys.argv[a+1]
    if sys.argv[a] == '--school':
        school = sys.argv[a+1]

username = username = os.popen('cat $TESTKEYS/schoolsoft.username').read()[:-1] #These cat lines can safely be removed, only used by me
password = os.popen('cat $TESTKEYS/schoolsoft.password').read()[:-1] #Yes i store my password in plaintext

 
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

    def fetch_lunch_menu(self):
        """
        Fetches the lunch menu for the entire week
        Returns an ordered list with days going from index 0-4
        This list contains all the food on that day
        """
        menu_html = self.try_get("https://sms5.schoolsoft.se/{}/jsp/student/right_student_lunchmenu.jsp?menu=lunchmenu".format(self.school))
        menu = BeautifulSoup(menu_html.text, "html.parser")

        lunch_menu = []

        for div in menu.find_all("td", {"style": "word-wrap: break-word"}):
            food_info = div.get_text(separator=u"<br/>").split(u"<br/>")
            lunch_menu.append(food_info)

        return lunch_menu

    def fetch_schedule(self):
        """
        Fetches the schedule of logged in user
        Returns an (not currently) ordered list with days going from index 0-4
        This list contains all events on that day
        """

        schedule_html = self.try_get("https://sms5.schoolsoft.se/{}/jsp/student/right_student_schedule.jsp?menu=schedule".format(self.school))
        schedule = BeautifulSoup(schedule_html.text, "html.parser")
        full_schedule = []

        for a in schedule.find_all("a", {"class": "schedule"}):
            info = a.find("span")
            info_pretty = info.get_text(separator=u"<br/>").split(u"<br/>")
            full_schedule.append(info_pretty)

        return (full_schedule, schedule)

api = SchoolSoft(school, username, password)
lunch = api.fetch_lunch_menu() #Sorted in an array
schedule = api.fetch_schedule()[0]

full = str(api.fetch_schedule()[1]) #Full schedule html
full = full.replace('<td','\n') #Helps the cutter script
full = re.sub('class="schedulecell" rowspan="6" width="5%">[0-9]*[0-9]:[0-9][0-9]</td>','',full) #Replaces unwanted rowspans, important for the script to work
count = full.count('rowspan=') 

begin = 0
rowspans = []
for a in range(count): #This for-loop finds all rowspans and appends them to rowspans[]
	start = full[begin:].find('rowspan')+begin+9
	rowspans.append(full[start:start+full[start:].find('"')])
	begin =full[begin:].find('rowspan')+begin + 1

schedule_list = [ [ [],[],[],[],[] ],[ [],[],[],[],[] ],[ [],[],[],[],[] ],[ [],[],[],[],[] ] ] #Stores everything in an easily accesible list

#schedule_list[0] = rowspans (This isn't really needed for general use, just calculations)
#schedule_list[1] = Class name 
#schedule_list[2] = Class time
#schedule_list[3] = Class location
#schedule_list[x][y][z]: y = day, z = class number (z = 0 means first class of the day) 
#Example:
#schedule_list[2][3] = Class times on day 3 (Thursday) 
#schedule_list[1][2][4] = Class name of the fifth class on day 2 (Wednesday)

for a in range(5): #Appends the first 5 rowspans
    schedule_list[0][a].append(int(rowspans[a]))

for b in range(len(rowspans)-5): #This is where the magic happends, it calculates where the schedules should be placed based on the block size    
    summa = [ [],[],[],[],[]  ]
    for c in range(5):
        summa[c].append(sum(schedule_list[0][c]))
    if (len(schedule_list[0][summa.index(min(summa))]))%2 != 0:
        schedule_list[1][summa.index(min(summa))].append(schedule[0][0])
        schedule_list[2][summa.index(min(summa))].append(schedule[0][1])
        schedule_list[3][summa.index(min(summa))].append(schedule[0][2])
        schedule.pop(0)

    schedule_list[0][summa.index(min(summa))].append(int(rowspans[5+b]))

for d in range(len(sys.argv)):
    if sys.argv[d] == '--lunch':
        print(lunch)
    if len(sys.argv[d]) == 1 and sys.argv[d] in '01234':
        day = int(sys.argv[d])
        for e in range(len(schedule_list[1][day])):
            print(schedule_list[1][day][e],end='') #end='' is to stop printing a new line
            print(' '+schedule_list[2][day][e]+' ',end='')
            print(schedule_list[3][day][e])



