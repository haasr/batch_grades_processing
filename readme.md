# D2L Batch Grades Processing System

A scalable Python application for automated scraping, processing, and database management of student grades from D2L (Desire2Learn) Learning Management System across multiple course sections.

## Table of Contents

- [Overview](#overview)
- [The Problem & Solution](#the-problem--solution)
- [Project Architecture](#project-architecture)
- [Database Schema](#database-schema)
- [Installation & Setup](#installation--setup)
- [Usage](#usage)
- [Module Documentation](#module-documentation)
- [Grade Calculation Logic](#grade-calculation-logic)
- [Extending the System](#extending-the-system)

---

## Overview

This system solves the combinatorial problem of tracking student grades across multiple lab and lecture sections in the Using Information Technology (UIT) course at ETSU. Students are enrolled in both a lecture course (CSCI-1100) and a lab course (CSCI-1150), with grades stored separately in D2L. The system automates grade retrieval, calculates overall grades, and maintains historical snapshots.

### Key Features

- **Automated Web Scraping**: Selenium-based scrapers for D2L grade exports
- **Parallel Processing**: Concurrent workers for efficient multi-section scraping
- **Database Persistence**: SQLAlchemy ORM with support for SQLite and PostgreSQL
- **Grade Calculations**: Automatic calculation of mid-term and final grades
- **Historical Tracking**: Timestamped snapshots of student grades over time
- **Flexible Configuration**: Environment-based configuration for different scenarios

---

## The Problem & Solution

### The Combinatorial Challenge

**Course Structure:**
- Students must register for BOTH:
  - **Lecture Course**: CSCI-1100 (multiple sections, e.g., CSCI-1100-001, CSCI-1100-901)
  - **Lab Course**: CSCI-1150 (54 sections, e.g., CSCI-1150-001 through CSCI-1150-042, plus online sections)

**The Problem:**
- Each course section has its own D2L gradebook
- To find a student's overall grade requires visiting multiple D2L sites
- With 54+ lab sections and multiple lecture sections, manual lookup is time-intensive
- Grade components are split across different courses

**The Solution:**
This system scrapes all grade data from all sections in parallel, stores it in a unified database, and enables instant retrieval of any student's complete grade profile.

### Grade Components

The overall grade is calculated from four components:

**From Lecture Course (CSCI-1100):**
1. **Quizzes Average** - Weekly quiz scores
2. **Exit Tickets Average** - Daily participation scores

**From Lab Course (CSCI-1150):**
3. **Lab Assignments Average** - Weekly lab completion scores
4. **Digital Citizenship Audit (DCA)** - Final project score

### Calculation Formulas

**Mid-term Grade (before final project deadline):**
```
Overall Grade = (Quizzes + Exit Tickets + Lab Assignments) / 3
```

**Final Grade (after final project submission):**
```
Pre-Final = (Quizzes + Exit Tickets + Lab Assignments) / 3
Overall Grade = (Pre-Final + DCA Score) / 2
```

---

## Project Architecture

### High-Level Structure

```
batch_grades/
├── database/          # Data models and database management
├── scraping/          # Web scraping components
├── workers/           # Parallel processing utilities
├── scrape.py          # Main driver script
├── requirements.txt   # Python dependencies
└── .env               # Environment configuration
```

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     D2L Web Interface                       │
│  (54+ Lab Sections + Multiple Lecture Sections)             │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   Scraping Layer                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │  OUScraper   │  │LabGrades     │  │LectureGrades │       │
│  │  (Discovery) │  │Scraper       │  │Scraper       │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              Worker Pool (Parallel Processing)              │
│  ┌──────────────────────┐  ┌──────────────────────┐         │
│  │ ChunkedWorkerPool    │  │ RoundRobinWorkerPool │         │
│  └──────────────────────┘  └──────────────────────┘         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   Database Layer                            │
│  ┌────────────┐  ┌────────────┐  ┌──────────────┐           │
│  │  Student   │  │   Course   │  │ GradeSnapshot│           │
│  │  Model     │  │   Model    │  │  Model       │           │
│  └────────────┘  └────────────┘  └──────────────┘           │
│                                                             │
│  ┌──────────────────────────────────────────────┐           │
│  │         StudentGrade (Aggregate)             │           │
│  └──────────────────────────────────────────────┘           │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow

1. **Discovery Phase**: `OUScraper` finds D2L Organizational Unit (OU) identifiers for each course section
2. **Scraping Phase**: `LabGradesScraper` and `LectureGradesScraper` download grade exports in parallel
3. **Processing Phase**: CSV files are parsed and transformed into pandas DataFrames
4. **Persistence Phase**: Data is saved to the database with automatic student/course creation
5. **Calculation Phase**: `StudentGrade` model calculates overall grades automatically

---

## Database Schema

### Entity Relationship Diagram

```
┌─────────────────┐
│    Student      │
├─────────────────┤
│ org_defined_id  │◄────┐
│ username        │     │
│ email           │     │
│ first_name      │     │
│ last_name       │     │
└─────────────────┘     │
                        │
                        │ 1:N
                        │
┌─────────────────┐     │         ┌─────────────────┐
│    Course       │     │         │ GradeSnapshot   │
├─────────────────┤     │         ├─────────────────┤
│ ou (PK)         │◄────┼─────────┤ id              │
│ course_name     │     │         │ student_id (FK) │
│ course_type     │     │         │ course_ou (FK)  │
│ section         │     │         │ snapshot_date   │
│ semester        │     │         │ lab_numerator   │
└─────────────────┘     │         │ lab_denominator │
                        │         │ lab_average     │
                        │         │ dca_score       │
                        │         │ quizzes_*       │
                        │         │ exit_tickets_*  │
                        │         └─────────────────┘
                        │
                        │
                        │
                        │         ┌─────────────────┐
                        │         │  StudentGrade   │
                        │         ├─────────────────┤
                        └─────────┤ id              │
                                  │ student_id (FK) │
                                  │ semester        │
                                  │ lab_course_ou   │
                                  │ lecture_course  │
                                  │ lab_average     │
                                  │ dca_score       │
                                  │ quizzes_average │
                                  │ exit_tickets_*  │
                                  │ overall_pre     │
                                  │ overall_post    │
                                  │ last_updated    │
                                  └─────────────────┘
```

### Table Descriptions

#### `students`
Primary student information table.
- **Primary Key**: `org_defined_id` (university-assigned student ID)
- **Indexed Fields**: `username`, `email`
- **Relationships**: One-to-many with `grade_snapshots` and `student_grades`

#### `courses`
Course section definitions.
- **Primary Key**: `ou` (D2L Organizational Unit identifier)
- **Fields**: 
  - `course_type`: 'LAB' or 'LECTURE'
  - `semester`: Format YYYYSS (e.g., 202580 = Fall 2025)
- **Constraints**: Check constraint on `course_type`

#### `grade_snapshots`
Historical point-in-time grade records.
- **Primary Key**: `id` (UUID)
- **Foreign Keys**: `student_id`, `course_ou`
- **Purpose**: Maintains complete history of grade changes over time
- **Indexes**: Composite index on `(student_id, course_ou, snapshot_date)`

#### `student_grades`
Current aggregate grade records per student per semester.
- **Primary Key**: `id` (UUID)
- **Unique Constraint**: `(student_id, semester)`
- **Foreign Keys**: 
  - `student_id` → students
  - `lab_course_ou` → courses
  - `lecture_course_ou` → courses
- **Calculated Fields**: 
  - `overall_grade_pre_final`: Mid-term grade
  - `overall_grade_post_final`: Final grade with DCA

### Semester Encoding

Semesters are encoded as `YYYYSS`:
- **Spring**: `YYYY10` (e.g., 202510)
- **Summer**: `YYYY50` (e.g., 202550)
- **Fall**: `YYYY80` (e.g., 202580)

This encoding is automatically calculated by `get_current_semester()` in `database/models.py`.

---

## Installation & Setup

### Prerequisites

- Python 3.12+ (developed with 3.12.2)
- Firefox browser (for Selenium)
- GeckoDriver (Firefox WebDriver)

### Installation Steps

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd batch_grades
   ```

2. **Create virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   
   Create `.env` file in project root:
   ```env
   # Database Configuration
   DB_TYPE=sqlite                    # or 'postgresql'
   DB_ECHO=False                     # Set to True for SQL logging
   
   # PostgreSQL Configuration (if DB_TYPE=postgresql)
   DB_USER=postgres
   DB_PASSWORD=your_password
   DB_HOST=localhost
   DB_PORT=5432
   DB_NAME=grades_db
   ```

   Create `scraping/.env` file:
   ```env
   # D2L Credentials
   MS_USERNAME=your_username         # Without @etsu.edu
   MS_PWD=your_password
   
   # Scraping Configuration
   MODIFY_GRADE_CALC_OPTIONS=1       # 1 to modify D2L settings, 0 to skip
   DROP_UNGRADED_ITEMS=0             # 1 to drop ungraded, 0 to treat as zero
   DELETE_DOWNLOADS_ON_COMPLETION=1  # 1 to cleanup CSV files
   
   # Grade Category Labels (must match D2L gradebook)
   LAB_ASSIGNMENTS_CATEGORY_LABEL=Lab
   FINAL_PROJECT_LABEL=Audit
   QUIZZES_CATEGORY_LABEL=Quizzes
   EXIT_TICKETS_CATEGORY_LABEL=Exit Tickets
   ```

5. **Initialize the database**
   ```bash
   python -m database.init_db
   ```

   To drop and recreate (⚠️ **WARNING**: Deletes all data):
   ```bash
   python -m database.init_db --drop
   ```

6. **Verify installation**
   ```bash
   python -m database.init_db  # Should show table creation messages
   ```

---

## Usage

### Basic Workflow

The scraping process follows three main phases:

1. **Discover OUs** - Find D2L organizational unit identifiers
2. **Scrape Lab Grades** - Download and process lab section grades
3. **Scrape Lecture Grades** - Download and process lecture section grades

### Running the Scraper

**Edit `scrape.py` to configure your semester and sections:**

```python
def main():
    semester = '202580'  # Fall 2025
    
    # Phase 1: Discover OUs (uncomment if needed)
    # scrape_ous(semester)
    
    # Phase 2: Scrape lab grades
    labs_csv = CURRENT_DIR / 'labs_ou_202580.csv'
    scrape_lab_grades(labs_csv)
    
    # Phase 3: Scrape lecture grades
    lecture_ous = ['10219699', '10219787']
    scrape_lecture_grades(lecture_ous)

if __name__ == '__main__':
    main()
```

**Run the scraper:**
```bash
python scrape.py
```

### Phase 1: Discovering OUs

OUs (Organizational Units) are D2L's internal identifiers for course sections. You need these before scraping grades.

```python
from scraping import OUScraper

semester = '202580'
sections = ['CSCI-1150-001', 'CSCI-1150-002', 'CSCI-1100-001']

with OUScraper(sections, semester, headless=True) as scraper:
    scraper.login()
    scraper.search_classes()
    
    # Results stored in scraper.ou_map
    for section, ou in scraper.ou_map.items():
        print(f"{section}: {ou}")
```

**Output format:**
```
CSCI-1150-001: 10219650
CSCI-1150-002: 10219651
CSCI-1100-001: 10219699
```

Save these to a CSV file for later use:
```csv
Section,OU
CSCI-1150-001,10219650
CSCI-1150-002,10219651
```

### Phase 2: Scraping Lab Grades

```python
from scraping import LabGradesScraper

lab_ous = ['10219650', '10219651']

with LabGradesScraper(lab_ous, headless=True) as scraper:
    scraper.login()
    dataframes = scraper.scrape_all_ous()
    scraper.save_grades_to_db()  # Saves to database
```

**What happens:**
1. Logs into D2L via Microsoft authentication
2. Configures grade export settings for each section
3. Exports grades to CSV files
4. Parses CSV files into pandas DataFrames
5. Creates/updates database records:
   - Student records
   - Course records
   - Grade snapshots (historical)
   - Student grade aggregates (current)

### Phase 3: Scraping Lecture Grades

```python
from scraping import LectureGradesScraper

lecture_ous = ['10219699', '10219787']

with LectureGradesScraper(lecture_ous, headless=True) as scraper:
    scraper.login()
    dataframes = scraper.scrape_all_ous()
    scraper.save_grades_to_db()  # Updates existing records
```

### Parallel Processing with Workers

The `ChunkedWorkerPool` enables parallel scraping across multiple sections:

```python
from workers import ChunkedWorkerPool
from scraping import LabGradesScraper

lab_ous = ['10219650', '10219651', '10219652', '10219653']

def scrape_labs(ous_list, headless=True):
    with LabGradesScraper(ous_list, headless=headless) as scraper:
        scraper.login()
        scraper.scrape_all_ous()
        scraper.save_grades_to_db()

# Split work across 2 parallel workers
pool = ChunkedWorkerPool(
    items=lab_ous,
    func=scrape_labs,
    func_args=(True,),  # headless=True
    num_workers=2
)

results = pool.run()
```

**Worker distribution:**
- Worker 1: ['10219650', '10219651']
- Worker 2: ['10219652', '10219653']

Each worker maintains its own browser session and logs to separate files.

---

## Module Documentation

### `database/` Package

#### `connection.py`
Database connection management with support for SQLite and PostgreSQL.

**Key Functions:**
- `get_db_session()`: Context manager for database sessions
- `get_db()`: Get a raw session object

**Configuration:**
- Reads from `.env` file in project root
- Defaults to SQLite at `grades.db`
- Supports connection pooling for PostgreSQL

#### `models.py`
SQLAlchemy ORM models defining the database schema.

**Models:**
- `Student`: Student demographic information
- `Course`: Course section definitions
- `GradeSnapshot`: Point-in-time grade records
- `StudentGrade`: Aggregate grade calculations

**Key Methods:**

`StudentGrade.calculate_overall_grades()`:
```python
def calculate_overall_grades(self):
    """
    Calculate pre-final and post-final overall grades.

    Post-final calculation:
    - If DCA graded (even if 0): (pre_final + dca_score) / 2
    - If DCA not graded yet: pre_final / 2 (shows penalty for non-submission)
    """
    components = []
    if self.lab_average is not None:
        components.append(self.lab_average)
    if self.quizzes_average is not None:
        components.append(self.quizzes_average)
    if self.exit_tickets_average is not None:
        components.append(self.exit_tickets_average)
    
    # Pre-final: average of available components
    if len(components) > 0:
        self.overall_grade_pre_final = sum(components) / 3
    else:
        self.overall_grade_pre_final = None
    
    # Post-final: always calculated to show potential/actual final grade
    if self.overall_grade_pre_final is not None:
        if self.dca_score is not None:
            # DCA graded: actual final grade
            self.overall_grade_post_final = (
                self.overall_grade_pre_final + self.dca_score
            ) / 2
        else:
            # DCA not graded: shows what grade would be without DCA
            self.overall_grade_post_final = self.overall_grade_pre_final / 2
    else:
        self.overall_grade_post_final = None
    
    return self.overall_grade_pre_final, self.overall_grade_post_final
```

**Properties:**
- `current_grade_pre_final`: Returns the pre-final grade (before DCA)
- `current_grade_post_final`: Returns the post-final grade (with DCA, or 50% penalty if not entered)
- `has_final_project`: Boolean indicating if DCA score has been entered (even if 0)

**Purpose of Separate Properties:**
The system displays BOTH grades simultaneously so students and instructors can see:
1. Their current performance (pre-final)
2. Their projected/actual final grade (post-final)

This makes it immediately obvious when a student needs to submit their DCA.

#### `init_db.py`
Database initialization and verification utilities.

**Functions:**
- `init_database(drop_existing=False)`: Create all tables
- `verify_database()`: Check that expected tables exist

**Usage:**
```bash
# Create tables
python -m database.init_db

# Drop and recreate
python -m database.init_db --drop
```

### `scraping/` Package

#### `d2l_grades_scraper.py`
Abstract base class for D2L grade scrapers providing common functionality.

**Key Features:**
- Firefox WebDriver configuration with anti-detection measures
- Microsoft SAML authentication flow
- Download directory management
- Per-worker logging
- CSV file tracking and cleanup

**Key Methods:**
- `login()`: Handle Microsoft authentication
- `set_calculation_options()`: Configure D2L grade calculation settings
- `export_users_grades()`: Abstract method for grade export
- `parse_data_from_grades_csv()`: Abstract method for CSV parsing
- `save_grades_to_db()`: Abstract method for database persistence

#### `lab_scraping.py`
Lab course grade scraper implementation.

**Exports:**
- Lab assignments subtotal (numerator/denominator)
- Digital Citizenship Audit (final project) score

**Parsing Logic:**
- Normalizes DCA scores to percentages
- Calculates lab averages
- Handles missing/ungraded assignments
- Uses mode to replace zero denominators (prevents division by zero)

**Database Operations:**
- Creates Student and Course records if missing
- Creates GradeSnapshot for historical tracking
- Updates StudentGrade with lab data
- Recalculates overall grades

#### `lecture_scraping.py`
Lecture course grade scraper implementation.

**Exports:**
- Quizzes subtotal (numerator/denominator)
- Exit Tickets subtotal (numerator/denominator)

**Parsing Logic:**
- Rounds exit ticket calculations to 6 decimal places (handles floating-point precision)
- Calculates component averages
- Uses mode to replace zero denominators

**Database Operations:**
- Creates Student records if missing
- Updates StudentGrade with lecture data
- Creates GradeSnapshot for historical tracking
- Recalculates overall grades

#### `ou_scraping.py`
Course section discovery scraper for finding D2L OUs.

**Usage Pattern:**
```python
classes = ['CSCI-1150-001', 'CSCI-1150-002']
semester = '202580'

with OUScraper(classes, semester, headless=True) as scraper:
    scraper.login()
    scraper.search_classes()
    print(scraper.ou_map)  # {'CSCI-1150-001': '10219650', ...}
```

**Search Algorithm:**
- Uses D2L's course search interface
- Matches course names with regex patterns
- Extracts OU from course URLs

### `workers/` Package

#### `RoundRobinWorkerPool`
Distributes items across workers in round-robin fashion.

**Distribution Example:**
```python
items = [1, 2, 3, 4, 5, 6, 7]
num_workers = 3

# Distribution:
# Worker 1: [1, 4, 7]
# Worker 2: [2, 5]
# Worker 3: [3, 6]
```

**Usage:**
```python
from workers import RoundRobinWorkerPool

def process_item(item):
    return item * 2

pool = RoundRobinWorkerPool(
    items=[1, 2, 3, 4, 5],
    func=process_item,
    num_workers=2
)

results = pool.run()  # [2, 4, 6, 8, 10]
```

#### `ChunkedWorkerPool`
Distributes items in contiguous chunks across workers.

**Distribution Example:**
```python
items = [1, 2, 3, 4, 5, 6, 7]
num_workers = 3

# Distribution (with remainder handling):
# Worker 1: [1, 2, 3]  (gets extra item)
# Worker 2: [4, 5]
# Worker 3: [6, 7]
```

**Usage:**
```python
from workers import ChunkedWorkerPool

def process_chunk(chunk, multiplier):
    return [x * multiplier for x in chunk]

pool = ChunkedWorkerPool(
    items=[1, 2, 3, 4, 5],
    func=process_chunk,
    func_args=(2,),  # Additional arguments
    num_workers=2
)

results = pool.run()  # [[2, 4, 6], [8, 10]]
```

**Key Difference:**
- `RoundRobinWorkerPool`: Function processes ONE item at a time
- `ChunkedWorkerPool`: Function processes ENTIRE chunk at once

---

## Grade Calculation Logic

### Data Flow for Grade Calculations

```
┌─────────────────────┐
│  Lab Scraper Run    │
│  - lab_average      │
│  - dca_score        │
└──────────┬──────────┘
           │
           ▼
    ┌─────────────┐         ┌──────────────────────┐
    │ StudentGrade│────────►│ calculate_overall    │
    │  (Database) │         │ _grades()            │
    └─────────────┘         └──────────────────────┘
           ▲                           │
           │                           │
┌──────────┴──────────┐                │
│ Lecture Scraper Run │                │
│ - quizzes_average   │                │
│ - exit_tix_average  │                │
└─────────────────────┘                │
                                       ▼
                        ┌──────────────────────────────┐
                        │  overall_grade_pre_final =   │
                        │  (labs + quizzes + exits)/3  │
                        └──────────────────────────────┘
                                       │
                                       ▼
                        ┌──────────────────────────────┐
                        │ overall_grade_post_final =   │
                        │ (pre_final + DCA)/2          │
                        │                              │
                        └──────────────────────────────┘
```

### Grade Component Weights

All components are **equally weighted** in the pre-final calculation:

| Component | Weight | Source Course |
|-----------|--------|---------------|
| Lab Assignments | 33.33% | CSCI-1150 (Lab) |
| Quizzes | 33.33% | CSCI-1100 (Lecture) |
| Exit Tickets | 33.33% | CSCI-1100 (Lecture) |

After the final project:

| Component | Weight |
|-----------|--------|
| Pre-final Grade | 50% |
| Digital Citizenship Audit | 50% |

### Handling Missing Data

**Philosophy**: Use zeros for missing assignments, not null values.

**Implementation:**
```python
# In CSV parsing
df['lab_numerator'] = df['lab_numerator'].fillna(0)
df['lab_denominator'] = df['lab_denominator'].fillna(0)

# Prevent division by zero using mode
denom_mode = float(df['lab_denominator'].mode()[0])
df['lab_denominator'] = df['lab_denominator'].replace(0, denom_mode)

# Calculate average
df['lab_average'] = 100 * (df['lab_numerator'] / df['lab_denominator'])
```

**Why mode for denominators?**
- Prevents division by zero errors
- Uses the most common total points value
- Maintains correct percentage calculation for students with zeros

### DCA Score States and Grade Display

The `dca_score` field has three possible states, but the system **always calculates both pre-final and post-final grades** to provide maximum visibility:

**State 1: DCA Not Yet Graded (`dca_score = None`)**
- Final project deadline hasn't passed, or grades haven't been entered
- `overall_grade_pre_final = (labs + quizzes + exit_tix) / 3`
- `overall_grade_post_final = pre_final / 2` ⚠️ **Shows 50% penalty**
- **Purpose**: Makes it obvious to students what will happen if they don't submit

**State 2: DCA Not Submitted (`dca_score = 0`)**
- Final project deadline passed, student didn't submit
- `overall_grade_pre_final = (labs + quizzes + exit_tix) / 3`
- `overall_grade_post_final = (pre_final + 0) / 2`
- **Result**: Same 50% penalty as State 1, but now official

**State 3: DCA Submitted (`dca_score > 0`)**
- Student submitted final project and received a grade
- `overall_grade_pre_final = (labs + quizzes + exit_tix) / 3`
- `overall_grade_post_final = (pre_final + dca_score) / 2`
- **Result**: Final grade reflects DCA performance

**Why Always Calculate Post-Final?**

By showing the post-final grade even when DCA is None, the system provides:
- **Early Warning**: Students see their potential final grade if they don't submit
- **Motivation**: The dramatic drop from pre-final to post-final is highly visible
- **Transparency**: No surprises when final grades are released

**Example Display:**
```python
# Student with 85% pre-final, DCA not yet graded
student_grade.dca_score = None
student_grade.calculate_overall_grades()

print(student_grade)
# Output:
# <StudentGrade E00123456 - 202580
#  - Pre-DCA:  85.00%
#  - Post-DCA: 42.50%>  ⚠️ Visual warning!
```

### Grade Rounding

**Exit Tickets**: Rounded to 6 decimal places (because digital exit ticket subtotals are slightly off!)
```python
df['exit_tickets_average'] = (
    100 * round(
        df['exit_tickets_numerator'] / df['exit_tickets_denominator'],
        6
    )
)
```

**Reason**: Digital exit tickets can produce floating-point precision issues (e.g., 49.999998333/50 should be 100%).

**Other Components**: No rounding (raw percentages)

### Example Calculations

All examples use the same student with consistent component grades:
- Lab Average: 85.5%
- Quizzes Average: 92.0%
- Exit Tickets Average: 88.3%

**Pre-final calculation** (same for all scenarios):
```
overall_grade_pre_final = (85.5 + 92.0 + 88.3) / 3
                        = 265.8 / 3
                        = 88.6%
```

**Scenario 1: Mid-Semester (DCA not yet graded)**

```python
dca_score = None
```

```
overall_grade_post_final = 88.6 / 2  # Shows penalty for missing DCA
                         = 44.3%

Display:
 - Pre-DCA:  88.6%  ← Current semester performance
 - Post-DCA: 44.3%  ← What final grade will be without DCA submission
```

**Purpose**: Student sees they're doing well (88.6%) but will fail (44.3%) if they don't submit DCA.

---

**Scenario 2: Student Didn't Submit DCA**

```python
dca_score = 0.0
```

```
overall_grade_post_final = (88.6 + 0.0) / 2
                         = 44.3%

Display:
 - Pre-DCA:  88.6%  ← Their earned grade before DCA
 - Post-DCA: 44.3%  ← Final grade with 0 on DCA (FAILING)
```

**Result**: Same 44.3% as Scenario 1, but now it's official - student failed the course.

---

**Scenario 3: Student Submitted DCA (Earned 95%)**

```python
dca_score = 95.0
```

```
overall_grade_post_final = (88.6 + 95.0) / 2
                         = 183.6 / 2
                         = 91.8%

Display:
 - Pre-DCA:  88.6%  ← Their semester performance
 - Post-DCA: 91.8%  ← Final grade with DCA (PASSING with A)
```

**Result**: Student's strong DCA performance (95%) elevated their final grade to 91.8%.

---

**Scenario 4: Student Submitted DCA (Earned 50%)**

```python
dca_score = 50.0
```

```
overall_grade_post_final = (88.6 + 50.0) / 2
                         = 138.6 / 2
                         = 69.3%

Display:
 - Pre-DCA:  88.6%  ← Good semester performance
 - Post-DCA: 69.3%  ← Final grade hurt by poor DCA (PASSING but low D)
```

**Result**: Even with poor DCA performance (50%), student still passes because their semester work was strong.

---

**Key Insight:**

The visual contrast between pre-final and post-final grades serves as:
1. **Motivation** during the semester (88.6% vs 44.3% - "I need to submit!")
2. **Transparency** after DCA submission (88.6% vs 91.8% - "My hard work paid off!")
3. **Accountability** for non-submission (88.6% vs 44.3% - "I should have submitted...")

---

## Extending the System

### Adding Query Tooling

The system is designed for extension with querying capabilities. Recommended approach:

#### 1. Create a `queries/` Package

```python
# queries/__init__.py
from .student_queries import StudentQueries
from .grade_queries import GradeQueries
from .report_queries import ReportQueries

# queries/student_queries.py
from database import get_db, Student, StudentGrade

class StudentQueries:
    @staticmethod
    def get_student_by_username(username: str):
        """Find student by username."""
        db = get_db()
        try:
            return db.query(Student).filter_by(username=username).first()
        finally:
            db.close()
    
    @staticmethod
    def get_current_grade(org_id: str, semester: str):
        """Get student's current overall grade."""
        db = get_db()
        try:
            grade = db.query(StudentGrade).filter_by(
                student_id=org_id,
                semester=semester
            ).first()
            return grade.current_grade if grade else None
        finally:
            db.close()
```

#### 2. Create Analysis Scripts

```python
# analyze.py
from queries import StudentQueries, GradeQueries

def analyze_student(username: str):
    student = StudentQueries.get_student_by_username(username)
    if not student:
        print(f"Student {username} not found")
        return
    
    grade = StudentQueries.get_current_grade(
        student.org_defined_id,
        '202580'
    )
    
    print(f"Student: {student.first_name} {student.last_name}")
    print(f"Current Grade: {grade:.2f}%")

if __name__ == '__main__':
    analyze_student('johndoe')
```

#### 3. Add Web Interface (Django/Flask)

Since you work with Django, you could build a web interface:

```python
# views.py (Django)
from django.shortcuts import render
from queries import StudentQueries

def student_grade_view(request, username):
    student = StudentQueries.get_student_by_username(username)
    context = {
        'student': student,
        'grade': StudentQueries.get_current_grade(
            student.org_defined_id,
            '202580'
        )
    }
    return render(request, 'grades/student.html', context)
```

#### 4. Create Reporting Tools

```python
# queries/report_queries.py
from database import get_db, StudentGrade
from sqlalchemy import func

class ReportQueries:
    @staticmethod
    def get_grade_distribution(semester: str, num_bins: int = 10):
        """Get grade distribution histogram data."""
        db = get_db()
        try:
            grades = db.query(StudentGrade.current_grade)\
                      .filter_by(semester=semester)\
                      .filter(StudentGrade.overall_grade_pre_final.isnot(None))\
                      .all()
            
            # Process into histogram bins
            # ...
        finally:
            db.close()
    
    @staticmethod
    def get_failing_students(semester: str, threshold: float = 60.0):
        """Get list of students below passing threshold."""
        db = get_db()
        try:
            return db.query(Student, StudentGrade)\
                    .join(StudentGrade)\
                    .filter(StudentGrade.semester == semester)\
                    .filter(StudentGrade.current_grade < threshold)\
                    .all()
        finally:
            db.close()
```

### Adding New Scrapers

To add scrapers for additional course types:

1. **Subclass `D2LGradesScraper`**:
```python
# scraping/homework_scraping.py
from .d2l_grades_scraper import D2LGradesScraper

class HomeworkGradesScraper(D2LGradesScraper):
    def export_users_grades(self, ou: str) -> bool:
        # Implement grade export logic
        pass
    
    def parse_data_from_grades_csv(self, course_name: str, ou: str):
        # Implement CSV parsing logic
        pass
    
    def save_grades_to_db(self, semester: str = None):
        # Implement database persistence
        pass
```

2. **Update database models** if new grade components are needed:
```python
# database/models.py
class StudentGrade(Base):
    # ... existing fields ...
    homework_average = Column(Float)
    homework_numerator = Column(Float)
    homework_denominator = Column(Float)
    
    def calculate_overall_grades(self):
        components = []
        if self.lab_average is not None:
            components.append(self.lab_average)
        # Add new component
        if self.homework_average is not None:
            components.append(self.homework_average)
        # ... rest of calculation
```

### Database Migration Strategy

When extending the schema:

1. **For SQLite** (development):
```bash
# Backup existing database
cp grades.db grades.db.backup

# Modify models.py
# Then recreate:
python -m database.init_db --drop
```

2. **For PostgreSQL** (production):

Use Alembic for migrations:
```bash
# Install alembic
pip install alembic

# Initialize alembic
alembic init alembic

# Create migration
alembic revision --autogenerate -m "Add homework fields"

# Apply migration
alembic upgrade head
```

---

## Troubleshooting

### Common Issues

**Issue**: Selenium can't find elements
- **Cause**: D2L's dynamic content loading (or worse... some evil D2L people changed something!)
- **Solution**: Increase wait times or use more robust wait conditions

**Issue**: Login fails with "element not clickable"
- **Cause**: Element is obscured or loading
- **Solution**: Add explicit waits before clicking elements, scroll into view before clicking

**Issue**: CSV parsing fails
- **Cause**: D2L changed export format
- **Solution**: Check column names in CSV and update parsing logic

**Issue**: Database constraint violations
- **Cause**: Duplicate student/grade records
- **Solution**: Check for existing records before insertion

### Logging

Each scraper creates detailed logs in `scraping/logs/`:
- Format: `<ScraperType>_<Timestamp>_<WorkerPID>.log`
- Example: `Lab_10-13-2025_14-30_12345.log`

**Log levels:**
- INFO: Normal operation
- WARNING: Non-critical issues
- ERROR: Failed operations
- DEBUG: Detailed execution traces (enable with `logger.setLevel(logging.DEBUG)`)

### Testing Individual Components

**Test database connection:**
```python
from database import get_db, Student

db = get_db()
students = db.query(Student).limit(5).all()
for s in students:
    print(s)
db.close()
```

**Test scraper login:**
```python
from scraping import LabGradesScraper

with LabGradesScraper(['10219650'], headless=False) as scraper:
    success = scraper.login()
    print(f"Login successful: {success}")
    input("Press Enter to close browser...")
```

---

## Understanding Grade Display Logic

**Why show both pre-final and post-final grades?**

The dual-grade display provides critical information:

**Before DCA Deadline:**
```python
student_grade.dca_score = None
# Pre-DCA:  85.0%  ← "I'm doing great!"
# Post-DCA: 42.5%  ← "But I'll fail if I don't submit DCA!"
```

**After DCA Deadline (not submitted):**
```python
student_grade.dca_score = 0.0
# Pre-DCA:  85.0%  ← "I did well during the semester..."
# Post-DCA: 42.5%  ← "But I failed the course."
```

**After DCA Deadline (submitted):**
```python
student_grade.dca_score = 95.0
# Pre-DCA:  85.0%  ← "I did well during the semester..."
# Post-DCA: 90.0%  ← "...and my DCA score made it even better!"
```

**Checking DCA Status:**

```python
from database import get_db, StudentGrade

db = get_db()
student_grade = db.query(StudentGrade).filter_by(
    student_id='E00123456',
    semester='202580'
).first()

print(f"Pre-DCA:  {student_grade.current_grade_pre_final:.2f}%")
print(f"Post-DCA: {student_grade.current_grade_post_final:.2f}%")
print(f"DCA Entered: {student_grade.has_final_project}")

if not student_grade.has_final_project:
    print("⚠️  DCA not yet graded - post-final shows 50% penalty")
elif student_grade.dca_score == 0:
    print("⚠️  Student did not submit DCA")
else:
    print(f"✓ DCA Score: {student_grade.dca_score:.2f}%")

db.close()
```

**Query Patterns:**

```python
# Find students who haven't submitted DCA (after deadline)
students_no_dca = db.query(Student, StudentGrade)\
    .join(StudentGrade)\
    .filter(StudentGrade.semester == '202580')\
    .filter(StudentGrade.dca_score == 0)\
    .all()

# Find students at risk (good pre-final, but post-final shows failure)
at_risk_students = db.query(Student, StudentGrade)\
    .join(StudentGrade)\
    .filter(StudentGrade.semester == '202580')\
    .filter(StudentGrade.current_grade_pre_final > 60)\
    .filter(StudentGrade.current_grade_post_final < 60)\
    .filter(StudentGrade.has_final_project == False)\
    .all()

# Find students who improved their grade with DCA
improved = db.query(Student, StudentGrade)\
    .join(StudentGrade)\
    .filter(StudentGrade.semester == '202580')\
    .filter(StudentGrade.has_final_project == True)\
    .filter(StudentGrade.current_grade_post_final > StudentGrade.current_grade_pre_final)\
    .all()
```

## Performance Considerations

### Scraping Performance

**Single-threaded scraping** (54 lab sections):
- ~12 seconds per section
- Total time: ~10.8 minutes

**Multi-threaded scraping** (6 workers):
- Total time: ~2-3 minutes
- Recommended: 2-6 workers (balance speed vs. D2L server load)

### Database Performance

**SQLite**:
- Suitable for development and small deployments
- Single-writer limitation
- Fast for reads

**PostgreSQL**:
- Recommended for production
- Better concurrency handling
- Connection pooling enabled

### Optimization Tips

1. **Batch database commits**: Commit after each section rather than each student
2. **Index frequently queried fields**: Already indexed in schema
3. **Use connection pooling**: Configured for PostgreSQL
4. **Adjust worker count**: Based on available CPU cores and network bandwidth

---

## Security Considerations

### Credential Management

**Never commit credentials to version control:**
```gitignore
.env
scraping/.env
*.db
downloads/*
logs/*
```

**Environment variables are loaded from:**
- `/database/.env` - Database configuration
- `/scraping/.env` - D2L credentials and scraper settings

### Data Privacy

- Student data is sensitive - ensure proper access controls
- Use encrypted connections for PostgreSQL in production
- Regularly audit database access logs
- Implement role-based access for query tools

---

---

## Appendix: File Descriptions

### Configuration Files

| File | Purpose |
|------|---------|
| `.env` (root) | Database connection settings |
| `scraping/.env` | D2L credentials and scraper configuration |
| `.gitignore` | Excludes sensitive files from version control |
| `requirements.txt` | Python package dependencies |
| `python_version.txt` | Tested Python version |

### Generated Files/Directories

| Path | Content |
|------|---------|
| `grades.db` | SQLite database file (if using SQLite) |
| `scraping/downloads/` | Downloaded CSV grade files (auto-cleaned) |
| `scraping/logs/` | Scraper execution logs |

### Helper Scripts

| Script | Purpose |
|--------|---------|
| `scrape.py` | Main driver for running scrapers |
| `database/init_db.py` | Database initialization utility |

---

## Quick Reference

### Most Common Commands

```bash
# Initial setup
python -m database.init_db

# Run full scraping workflow
python scrape.py

# Reset database (CAUTION!)
python -m database.init_db --drop
```

### Most Common Queries

```python
from database import get_db, Student, StudentGrade

db = get_db()

# Find student by username
student = db.query(Student).filter_by(username='johndoe').first()

# Get student's current grade
grade = db.query(StudentGrade).filter_by(
    student_id=student.org_defined_id,
    semester='202580'
).first()

print(f"Current grade: {grade.current_grade:.2f}%")

db.close()
```

### Grade Display Reference

```python
from database import get_db, StudentGrade

db = get_db()
grade = db.query(StudentGrade).filter_by(
    student_id='E00123456',
    semester='202580'
).first()

# Access grades
pre_final = grade.current_grade_pre_final   # Semester performance
post_final = grade.current_grade_post_final # Final grade (actual or projected)

# Check DCA status
has_dca = grade.has_final_project          # True if DCA entered (even if 0)
dca_value = grade.dca_score                # Actual DCA score or None

# Display
print(grade)  # Shows both grades in formatted output

db.close()
```

**Grade Interpretation:**
- `pre_final > post_final` and `has_final_project = False`: ⚠️ Student needs to submit DCA
- `pre_final > post_final` and `has_final_project = True`: Student submitted but scored low
- `pre_final < post_final`: DCA improved their grade
- `pre_final ≈ post_final` and `dca_score ≈ pre_final`: Consistent performance

---

**Last Updated**: October 2025  
**Python Version**: 3.12.2  
**Database Schema Version**: 1.0
