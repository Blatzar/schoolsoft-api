# schoolsoft-api
Super crappy schoolsoft api to get the schedule in order and the lunch menu

<h2>How do i start it?</h2>

<code>python3 schoolsoft.py --username username --password password --school school --lunch</code>
To get the lunch in a list

Not conformable storing the password in the shell history? Use --ask instead of --password
<code>python3 schoolsoft.py --username username --ask --school school --lunch</code>

<code>python3 schoolsoft.py --username username --password password --school school --html</code>
To get the schedule html page

<code>python3 schoolsoft.py --username username --password password --school school 2</code>
To get the schedule for day 2 (Wednesday)

<h2>How does the schedule sorting work?</h2>
All the blocks in the scheme have a rowspan (basically size). What I did was place the classes from schoolsoft.py (sorted by time) in the day with the lowest rowspan.
For example if the rowspans of the time between 8:00 and the first class are: [22,24,7,18,16] you can deduct that the first class (by time) is going to be on Wednesday. Repeating this you can eventually get the whole scheme.
It's reccomended that you look at the html and rowspan on schoolsoft to understand better.

<h2>Credits</h2>
The schoolsoft login was copied from this python script
https://github.com/lnus/schoolsoft-api
