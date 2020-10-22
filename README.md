# schoolsoft-api
Super crappy schoolsoft api to get the schedule in order and the lunch menu

## How do I use it as a library?

Simple!

```python
api = SchoolSoft(school, username, password, usertype (optional))
```

## What does it do?

Currently pre-programmed calls are:

```python
api.fetch_lunch_menu()  # Gets the lunch menu and returns a list
api.fetch_schedule()    # Gets the schedule and returns a list
api.fetch_tests()       # Gets the upcoming tests and returns a dict
```

However, you can access almost any page by experimenting with:

```python
api.try_get(url)        # Runs a login call, and returns URL entered in request format
```


## How do I use it from the command line?

```bash
python3 schoolsoft.py --username username --password password --school school --lunch
``` 

To get the lunch in a list

Not conformable storing the password in the shell history? Use --ask instead of --password

```bash
python3 schoolsoft.py --username username --ask --school school --lunch
```

```bash
python3 schoolsoft.py --username username --password password --school school --schedule 2
```
To get the schedule for day 2 (Wednesday)

```bash
python3 schoolsoft.py --username username --password password --school school --tests
```
To get the upcoming tests


<h2>How does the schedule sorting work?</h2>

The schedule HTML needs more maths than expected to sort all schedule blocks in separate days. Block positions are determined by the position of the block before. 

All the blocks in the schedule have a rowspan (height). Repeatedly appending the next block to the day with the lowest amount of rowspans you can build a sorted schedule. 
For example if the rowspans of the time between 8:00 and the first class are: `[22, 24, 7, 18, 16]` you can deduct that the first class (by time) is going to be on Wednesday. Repeating this you can eventually get the whole schedule. 

Only this doesn't work on schedules with multiple lessons simultaneously, therefore the width also has to be accounted for in calculations, only adding the block's rowspan once the horizontal schedule is filled. 

<h2>Credits</h2>
The schoolsoft login was copied from this python script
https://github.com/lnus/schoolsoft-api
