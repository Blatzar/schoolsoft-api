#!/usr/bin/env python3
from bs4 import BeautifulSoup
import requests, re, os, sys
from time import gmtime, strftime 
from getpass import getpass #password

lunchtime = 40 #Minimum lunch time (minutes), used to calculate where the lunch is
lunchtoggle = True #False if you don't want to print the lunch
username = ''
password = ''
school = 'nacka' #if your schoolsoft-url is "https://sms13.schoolsoft.se/nacka/" then the schoolname is "nacka"
english = False #Language of the days

try:
    import testkeys #To import my own login details, you can remove this
    testkeys = testkeys.school()
    school = testkeys.school
    username = testkeys.username
    password = testkeys.password
except ImportError:
    pass

if english:days = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']
else:days = ['Måndag','Tisdag','Onsdag','Torsdag','Fredag','Lördag','Söndag']

for a in range(len(sys.argv)):
    if sys.argv[a] == '--ask':
        password = getpass()
    if sys.argv[a] == '--password':
        password = sys.argv[a+1]
    if sys.argv[a] == '--username':
        username = sys.argv[a+1]
    if sys.argv[a] == '--school':
        school = sys.argv[a+1]

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

        return (full_schedule, str(schedule))
    
    def fetch_tests(self):
        tests = self.try_get("https://sms5.schoolsoft.se/{}/jsp/student/right_student_test_schedule.jsp?menu=test_schedule".format(self.school))
        tests = str(BeautifulSoup(tests.text, "html.parser"))
        return(tests)

api = SchoolSoft(school, username, password) #__init__


lunch = api.fetch_lunch_menu() #Sorted in an array
schedule,full = api.fetch_schedule() #schedule
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
tests = [ [],[],[],[]    ] 
#tests[0] = day of the test, starting from 0
#tests[1] = label of the test, eg Test, Homework
#tests[2] = Title of the test and more info
#tests[3] = Week of the test
#example of a week with 2 tests
#[[0, 1], ['Prov', 'Prov'], ['Litteraturprov SVESVE02', 'Prov: psykodynamiskt perspektiv och beteendeperspektiv PSKPSY01'], [51, 51]]
for b in range(len(mid)):
        titleindex = 0
        labelindex = 0
        for a in range(mid[b].count('<label>')): #multiple tests on the same day
            label = ((re.search('<label>[\W\w]*?<\/label>',mid[b][labelindex:]))).group(0).strip('<label>').strip('</label>')  #gets the label (Test, Homework, etc) 
            day = int(str(re.search('day=[0-6]',mid[b]).group(0)).strip('day=')) #day of the test
            tests[0].append(day)
            tests[1].append(label)
            tests[3].append(round((b/6)-0.5)+weekinfo[1][0])
            if 'title="' in mid[b]: #gets the info on the test
                title = re.search('title="[\W\w\n]*?"',mid[b][titleindex:]).group(0).strip('title"').replace('\r\n">',' ')[2:-1] #Title can have max 50 characters, change regex if needed
                tests[2].append(title)
            titleindex = mid[b][titleindex:].find('title="') + titleindex + 1 #Finds the location of the title
            labelindex = mid[b][labelindex:].find('<label>') + labelindex + 1
        if 'valign="top">v' in mid[b]: #gets the week
            start = (mid[b]).find('valign="top"')+13 #could be done with regex, but this already works
            stop = (mid[b])[start:].find('<')+start
            week = int((mid[b])[start+1:stop])
            weekinfo[1].append(week)
            weekinfo[0].append(b)
    
    
full = full.replace('<td','\n') #Helps the cutter script
full = re.sub('class="schedulecell" rowspan="6" width="5%">[0-9]*[0-9]:[0-9][0-9]</td>','',full) #Replaces unwanted rowspans, important for the script to work
count = full.count('rowspan=') 

begin = 0
rowspans = []
for a in range(count): #This for-loop finds all rowspans and appends them to rowspans[], useful for getting the schedule sorted
	start = full[begin:].find('rowspan')+begin+9
	rowspans.append(full[start:start+full[start:].find('"')])
	begin =full[begin:].find('rowspan')+begin + 1

schedule_list = [ [ [],[],[],[],[] ],[ [],[],[],[],[] ],[ [],[],[],[],[] ],[ [],[],[],[],[] ],[ [],[],[],[],[] ] ] #Stores everything in an easily accesible list

#schedule_list[0] = rowspans (This isn't really needed for general use, just calculations)
#schedule_list[1] = Class name 
#schedule_list[2] = Class time
#schedule_list[3] = Class location
#schedule_list[4] = Class time (formatted diffrently)
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
        schedule_list[3][summa.index(min(summa))].append((schedule[0][2]).replace('\r\n',''))
        schedule.pop(0)
    schedule_list[0][summa.index(min(summa))].append(int(rowspans[5+b]))

for a in range(5): #Time formatted diffrently, useful for other script
    for b in range(len(schedule_list[2][a])):
        sep = schedule_list[2][a][b].find('-')
        schedule_list[4][a].append(schedule_list[2][a][b][:sep])
        schedule_list[4][a].append(schedule_list[2][a][b][sep+1:])

if lunchtoggle: #adds lunch to the schedule, based on break time
    for x in range(5):
        for y in range(len(schedule_list[0][x])-2):
            if y%2==0 and y != 0:
                if int(schedule_list[0][x][y]) > lunchtime/5:
                    schedule_list[1][x].insert(int(y/2),'Lunch')
                    schedule_list[2][x].insert(int(y/2),'')
                    schedule_list[3][x].insert(int(y/2),'')
                    schedule_list[4][x].insert(y,schedule_list[4][x][y-1])
                    schedule_list[4][x].insert(y+1,schedule_list[4][x][y+1])


prefix = ''
api = False
for d in range(len(sys.argv)):
    if sys.argv[d] == '--lunch':
        if api:
            for f in range(len(lunch)):
                print('n'+str(f)+'="'+lunch[f][0]+'"')
                if len(lunch[f]) > 1:
                    print('v'+str(f)+'="'+lunch[f][1]+'"')
        else:
             for f in range(len(lunch)):
                print(lunch[f][0])
                if len(lunch[f]) > 1:
                    print(lunch[f][1]+'\n')
    if sys.argv[d] == '--api':
        api = True
    if sys.argv[d] == '--raw-schedule':
        print(schedule_list)
    if sys.argv[d] == '--raw-lunch':
        print(lunch)
    if sys.argv[d] == '--discord':
        prefix = '**'
    if sys.argv[d] == '--tests':
        if len(tests[0]) == 0:
            if english:
                print('No tests upcoming')
            else:
                print('Inga prov eller läxor')
        else:
            for a in range(len(tests[0])):
                if tests[3][a] != tests[3][a-1]:
                    print(prefix+'Vecka: '+prefix+str(tests[3][a]))
                print(prefix+days[tests[0][a]]+prefix+'\n'+tests[1][a]+': '+tests[2][a])
    if (len(sys.argv[d]) == 1 and sys.argv[d] in '01234') or sys.argv[d] == '--day':
        if sys.argv[d] == '--day':
            day = (int(strftime("%w", gmtime()))-1)
        else:day = int(sys.argv[d])
        if api:
            print('{')
        for e in range(len(schedule_list[1][day])):
            if api:
                print(str(e) + '="',end='')
            print(schedule_list[1][day][e],end='') #end='' is to stop printing a new line
            if schedule_list[1][day][e] != 'Lunch':
                print(' ' + prefix+schedule_list[2][day][e]+prefix + ' ',end='')
            print(schedule_list[3][day][e],end='') #[:-2] to remove \n\r, remove this if it only partly prints classroom names
            if api:
                print('"')
            else:print('')
        if api:
            print('}')
