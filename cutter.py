#!/usr/bin/env python3
import os
from ast import literal_eval
import sys
#os.popen("sed -i -e 's/<td/\n/g' fulloutput.html")
command = 'python3 $SCRIPTS/schoolsoft.py --html | grep -v \'class="schedulecell" rowspan="6" width="5%">[\s\S\\0-9]*[0-9]:[0-9][0-9]</td>\' | grep schedulecell | grep rowspan'
full = os.popen(command).read()[:-1] #Gets the needed parts of the html code from schoolsoft.py
count = full.count('rowspan=') 
schedule = (os.popen('python3 $SCRIPTS/schoolsoft.py --schedule').read()[:-1]) #Reads the schedule (not html)
schedule = schedule.replace('\\r\\n','') #Removes unnecessary text
schedule = literal_eval(schedule) #Convert string to list


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
if len(sys.argv) > 1: #This isn't needed, I just use it for my discord bot
    if sys.argv[1][0:1] in '01234': #"python3 cutter.py 2" prints all the info of the 2:nd day
        day = int(sys.argv[1][0:1]) 
        for a in range(len(schedule_list[1][day])):
            print(schedule_list[1][day][a],end=' ') #end='' is to stop printing a new line
            print('**'+schedule_list[2][day][a]+'**',end=' ') # '**' for the discord bot I use, can safely be removed
            print(schedule_list[3][day][a])
