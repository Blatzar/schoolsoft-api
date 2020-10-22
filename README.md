# schoolsoft-api
Super crappy schoolsoft api to get the schedule in order and the lunch menu

<h2>How do i start it?</h2>

<code>python3 schoolsoft.py --username *username* --password *password* --school *school* --lunch</code>
To get the lunch in a list

Not conformable storing the password in the shell history? Use --ask instead of --password

<code>python3 schoolsoft.py --username *username* --ask --school *school* --lunch</code>

<code>python3 schoolsoft.py --username *username* --password *password* --school *school* --schedule 2</code>
To get the schedule for day 2 (Wednesday)

<code>python3 schoolsoft.py --username *username* --password *password* --school *school* --tests</code>
To get the upcoming tests

<h2>How does the schedule sorting work?</h2>

The schedule HTML needs more maths than expected to sort all schedule blocks in separate days. Block positions are determined by the position of the block before. 

All the blocks in the schedule have a rowspan (height). Repeatedly appending the next block to the day with the lowest amount of rowspans you can build a sorted schedule. 
For example if the rowspans of the time between 8:00 and the first class are: `[22, 24, 7, 18, 16]` you can deduct that the first class (by time) is going to be on Wednesday. Repeating this you can eventually get the whole schedule. 

Only this doesn't work on schedules with multiple lessons simultaneously, therefore the width also has to be accounted for in calculations, only adding the block's rowspan once the horizontal schedule is filled. 

<h2>Credits</h2>
The schoolsoft login was copied from this python script
https://github.com/lnus/schoolsoft-api
