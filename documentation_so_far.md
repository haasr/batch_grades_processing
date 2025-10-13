# D2L Batch Grades Processing

## Project Structure

```
batch_grades
├── database/
│   ├── __init__.py
│   ├── models.py          # SQLAlchemy models
│   ├── connection.py      # Database connection/session management
│   ├── init_db.py         # Database initialization script
│   └── .env               # Environment variables read by the connection module
├── scraping/
│   ├── __init__.py
│   ├── .env
│   ├── downloads              # Where downloaded grade files are stored
│   ├── logs                   # Where scraping log files are stored
│   ├── d2l_grades_scraper.py  # Contains the parent class of LectureGradesScraper and LabGradesScraper
│   ├── lab_scraping.py        # Contains LabGradesScraper class
│   ├── lecture_scraping.py    # Contains LectureGradesScraper class
│   ├── ou_scraping.py         # Contains OUScraper class
│   └── .env                   # Environment variables read by the scraper classes
├── workers/
│   └── __init__.py        # Classes for splitting up a function to run over an item or chunk of items from a list across multiple parallel jobs\
├── .venv                  # Virtual environment used
├── python_version.txt     # Version I used (3.12.2)
├── requirements.txt       # Dependencies
└── scrape.py              # Driver that uses scrapers (Just for testing so far)
```

## Context about how I calculate grades

### Lecture course and lab course

My Using Information Technology (UIT) students must be registered for both a lecture course and a lab course.
The Lecture course name is "CSCI-1100" and the Lab course name is "CSCI-1150". A section code is a
three-digit code that is appended with a hyphen after the course name, e.g. "CSCI-1100-001" or
"CSCI-1150-001".

### Grade Calculations
To calculate a student's overall UIT grade, we need several grade components:
1. The student's "Quizzes" and "Exit Tickets" averages, from the lecture course
2. The student's "Lab Assignments" average and "Digital Citizenship Audit" (final project) score from the lab course.

#### Calculating Mid-term grades or grades before final grades are due:

Prior to the final project deadline, the student's overall grade is calculated as such:
(Quizzes Average + Exit Tickets Average + Lab Assignments Average)/3

After the final project deadline, I must calculate the student's final grade as such:
((Quizzes Average + Exit Tickets Average + Lab Assignments Average)/3 + Digital Citizenship Audit Score)/2

### Purpose of This Project: Dealing with the Combinatorial Problem
The problem is that I have 54 lab sections and multiple lecture sections. When someone wants to know their overall
grade, it takes a while to look up all their grades because I visit multiple D2L sites (D2L is where they are stored).

These scrapers will scrape all the information I need from each of the lab section grade sites and lecture section D2L sites.
The goal is that by scraping and creating grade records in the database, I can easily retrieve a student's overall grade, both
pre-final-project and post-final-project.


## Initializing the Database:

# From project root
python -m database.init_db

# To drop and recreate (CAUTION!)
python -m database.init_db --drop

