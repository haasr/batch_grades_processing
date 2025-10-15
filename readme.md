# CSCI 1100 Grades Processing System

A comprehensive system for scraping, storing, querying, and exporting CSCI 1100 student grades from D2L (Desire2Learn).
Built for managing large courses with multiple lab and lecture sections.

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
    - [Architecture Details](./ARCHITECTURE.md)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Quick Reference Card](./QUICKREF.md)
- [Usage](#usage)
  - [Scraping Grades](#scraping-grades)
  - [Using the CLI](#using-the-cli)
  - [Query System](#query-system)
- [Database Schema](#database-schema)
- [Troubleshooting](#troubleshooting)
- [Development](#development)

---

## Overview

This system automates the entire workflow of managing grades for courses with:
- **52+ lab sections** (CSCI-1150-001 through CSCI-1150-909)
- **2 lecture sections** (CSCI-1100-001 and CSCI-1100-901)
- **1700+ students** across in-person and online cohorts

### What It Does

1. **Scrapes** grades from D2L using Selenium (parallel processing)
2. **Stores** grades in SQLite database with full history
3. **Queries** student data with powerful filtering and search
4. **Exports** grades in various formats (D2L imports, Excel workbooks, CSV)
5. **Analyzes** cohort performance and identifies at-risk students

---

## Features

### Phase I: Data Collection
- ✓ Parallel web scraping of D2L grade exports
- ✓ Automatic grade calculation (lab, quizzes, exit tickets, DCA)
- ✓ Worker pool architecture for fast batch processing
- ✓ Configurable section ranges (in-person, online, special sections)

### Phase II: Query System
- ✓ Student lookup by username, org ID, or fuzzy name search
- ✓ Section-based queries (view all students in a section)
- ✓ Cohort analysis (in-person vs online comparisons)
- ✓ At-risk student identification
- ✓ Professional formatting and statistics

### Phase III: Export & Reporting
- ✓ **D2L ESPR Export** - Midterm grades in D2L import format
- ✓ **D2L Final Export** - End-of-term grades in D2L import format
- ✓ **Lab Instructor Workbook** - Excel file with 56 sheets
  - One sheet per lab section (52 sheets)
  - Two lecture cohort sheets (in-person and online)
  - Two summary statistics sheets
- ✓ **CSV Exports** - Flexible exports for any query
- ✓ **Grade Distribution Reports** - Statistics with A/B/C/D/F breakdowns

### Command Line Interface
- ✓ Unified CLI for all operations
- ✓ Interactive menus with clear prompts
- ✓ Professional formatting with colors and tables
- ✓ Built-in help and error handling

---

## Architecture

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
                              ▲
                              │
┌─────────────────────────────────────────────────────────────┐
│                    Query System                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │
│  │  Student    │  │  Section    │  │  Cohort     │          │
│  │  Queries    │  │  Queries    │  │  Queries    │          │
│  └─────────────┘  └─────────────┘  └─────────────┘          │
│                                                             │
│  ┌──────────────────────────────────────────────┐           │
│  │         GradeFormatter (Output)              │           │
│  └──────────────────────────────────────────────┘           │
└─────────────────────────────────────────────────────────────┘
                              ▲
                              │
┌─────────────────────────────────────────────────────────────┐
│                  User Interface Layer                       │
│  ┌──────────────────────┐  ┌──────────────────────┐         │
│  │   CLI Interface      │  │   Programmatic API   │         │
│  │   (Interactive)      │  │   (Automation)       │         │
│  └──────────────────────┘  └──────────────────────┘         │
│                                                             │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐             │
│  │ D2L ESPR   │  │ D2L Final  │  │ Lab        │             │
│  │ Export     │  │ Export     │  │ Workbook   │             │
│  └────────────┘  └────────────┘  └────────────┘             │
└─────────────────────────────────────────────────────────────┘

```
### Architecture Details

To see more details, see the standalone [Architecture readme](./ARCHITECTURE.md)

### Directory Structure

```
batch_grades/
├── scraping/
│   ├── base_scraper.py          # Base class for all scrapers
│   ├── ou_scraper.py            # Scrapes course OUs
│   ├── lab_scraping.py          # Lab grades scraper
│   ├── lecture_scraping.py      # Lecture grades scraper
│   └── downloads/               # Downloaded CSV files
│
├── database/
│   ├── __init__.py              # Database connection
│   ├── models.py                # SQLAlchemy models
│   ├── init_db.py               # Database initialization
│   └── connection.py            # Session management
│
├── queries/
│   ├── __init__.py              # Query exports
│   ├── student_queries.py       # Individual student lookups
│   ├── section_queries.py       # Section-based queries
│   ├── cohort_queries.py        # Cohort analysis queries
│   └── formatting.py            # Professional output formatting
│
├── workers.py                   # Worker pool for parallel scraping
├── scrape.py                    # Main scraping orchestrator
├── cli.py                       # Command line interface
├── test_queries.py              # Query system tests
├── diagnose_database.py         # Database health checker
└── grades.db                    # SQLite database
```

### Layer Descriptions

**D2L Web Interface:**
- Source of all grade data
- 52 lab sections + 2 lecture sections
- Accessed via Selenium automation

**Scraping Layer:**
- Three specialized scrapers (OU, Lab, Lecture)
- Handles authentication and navigation
- Downloads grade exports as CSV files

**Worker Pool:**
- Parallel processing for fast scraping
- Two strategies: Chunked and RoundRobin
- Avoids database access during scraping

**Database Layer:**
- SQLite storage with SQLAlchemy ORM
- Four main models: Student, Course, StudentGrade, GradeSnapshot
- Automatic grade calculation
- Sequential saves (thread-safe)

**Query System (Phase II):**
- Three query modules: Student, Section, Cohort
- Professional formatting for console output
- Returns structured dictionaries
- No direct database access from CLI

**User Interface Layer (Phase III):**
- Interactive CLI with 10 features
- Programmatic API for automation
- Export capabilities (D2L, Excel, CSV)
- Professional reports and statistics

### Design Principles

1. **Separation of Concerns**
   - Scrapers handle data collection
   - Models handle data storage
   - Queries handle data retrieval
   - CLI handles user interaction

2. **Parallel Processing**
   - Worker pools for scraping (fast!)
   - Sequential database saves (safe!)
   - Avoids SQLite threading issues

3. **Professional Output**
   - Formatted tables for console
   - Styled Excel workbooks
   - D2L-compatible CSV exports

---

## Installation

### Prerequisites

- Python 3.12.2
- Google Chrome browser
- ChromeDriver (compatible with your Chrome version)

### Setup

```bash
# Clone the repository
cd batch_grades

# Install dependencies
pip install -r requirements --break-system-packages # Arg added for openpyxl

# Initialize the database
python -m database.init_db

# Verify installation
python diagnose_database.py
```

---

## Quick Start

### 1. Configure Sections

Edit `scrape.py` to set your sections:

```python
# Lab sections to scrape
labs = ["CSCI-1150-001", "CSCI-1150-002", ...]

# Lecture sections to scrape
lectures = ["CSCI-1100-001", "CSCI-1100-901"]
```

### 2. Scrape Grades

```bash
# Full workflow
python scrape.py

# This will:
# 1. Scrape OUs for all sections (parallel)
# 2. Scrape lab grades (parallel)
# 3. Scrape lecture grades (parallel)
# 4. Save to database (sequential)
```

### 3. Use the CLI

```bash
# Launch interactive interface
python cli.py

# Or specify semester
python cli.py 202610
```

## Quick Reference Card

See the [Quick Reference Card](./QUICKREF.md) to simplify usage.

## 📖 Usage

### Scraping Grades

The scraping system uses a **two-phase approach**:

**Phase 1: Parallel Scraping (Fast)**
- Multiple workers scrape sections simultaneously
- Downloads CSV files from D2L
- Processes grade data into DataFrames
- No database access (safe for parallel execution)

**Phase 2: Sequential Saving (Safe)**
- Main thread saves each section one at a time
- Avoids SQLite threading conflicts
- Provides detailed logging and error handling

#### Scrape Workflow

```python
# scrape.py structure

# Step 1: Find course OUs
scrape_ous(semester='202580')
# Output: labs_ou_202580.csv, lectures_ou_202580.csv

# Step 2: Scrape lab grades
scrape_lab_grades('labs_ou_202580.csv')
# Workers scrape in parallel
# Main thread saves sequentially

# Step 3: Scrape lecture grades
scrape_lecture_grades(['10219691', '10219784'])
# Workers scrape in parallel
# Main thread saves sequentially
```

#### Scraping Options

```python
# Number of parallel workers
num_workers=2  # Adjust based on your system

# Headless mode
headless=True  # Run without visible browser

# Section ranges
inperson_start=1
inperson_end=42
online_start=901
online_end=909
```

### Using the CLI

The CLI provides 10 main features organized into categories:

#### Query & View (Options 1-5)

**1. Lookup Student**
```
Search by:
  1. Username (exact match)
  2. Org Defined ID (exact match)
  3. Name (fuzzy search)

Shows complete grade profile with:
- Personal information
- Lab grades and DCA score
- Lecture grades (quizzes and exit tickets)
- Pre-final and post-final overall grades
- Section assignments

Option to export to CSV
```

**2. View Section Grades**
```
Lists all available sections:
- 52 lab sections
- 2 lecture sections

Select a section to view:
- All enrolled students
- Grade statistics
- Section averages

Option to export to CSV
```

**3. Compare Cohorts**
```
Side-by-side comparison of:
- In-person students (sections 001-899)
- Online students (sections 900+)

Shows:
- Total students
- Average grades by component
- Passing rates (pre and post final)
- Statistical comparison

Option to export both cohorts
```

**4. Find At-Risk Students**
```
Two modes:

Mode 1: Pre-final (before DCA deadline)
- Shows students with pre-final < 60%
- Breakdown by severity:
  * Critically at-risk (0-50%)
  * Very at-risk (50-55%)
  * At-risk (55-60%)
- Use for early intervention

Mode 2: Post-final (after DCA graded)
- Shows students passing pre-final but failing post-final
- Highlights students who haven't submitted DCA
- Use for final grade decisions

Option to export list
```

**5. Find Students Missing DCA**
```
Lists all students who haven't submitted the final project

Shows:
- Student information
- Current grade without DCA
- Section assignments

Option to export list
```

#### Export & Report (Options 6-8)

**6. Generate Lab Instructor Workbook**
```
Creates comprehensive Excel workbook with 56 sheets:

Lab Section Sheets (52):
- One sheet per lab section
- Columns: Last Name, First Name, Username, Email, Lab Avg, DCA
- Sorted alphabetically
- Professional formatting

Lecture Cohort Sheets (2):
- In-Person Lecture (all in-person students)
- Online Lecture (all online students)
- Full grade breakdowns
- Includes lab section assignments

Summary Statistics Sheets (2):
- In-Person Summary (statistics and distribution)
- Online Summary (statistics and distribution)
- Grade distribution (A/B/C/D/F counts)
- Average grades by component
- Passing rates

Output: lab_workbook_SEMESTER.xlsx
```

**7. Export ESPR Grades (D2L format)**
```
Exports midterm grades in D2L-compatible format

Select cohort:
  1. In-person students only
  2. Online students only
  3. All students

Format:
  Username, OrgDefinedId, ESPR Points Grade, End-of-Line Indicator
  johndoe,E00123456,87.45,#

Uses: overall_pre_final grade
Output: d2l_espr_COHORT_SEMESTER.csv

Ready to import directly into D2L:
1. D2L → Grades → Import
2. Select CSV file
3. Map to ESPR grade column
```

**8. Export Final Grades (D2L format)**
```
Exports final grades in D2L-compatible format

Select cohort:
  1. In-person students only
  2. Online students only
  3. All students

Format:
  Username, OrgDefinedId, End-of-Term Points Grade, End-of-Line Indicator
  johndoe,E00123456,89.23,#

Uses: overall_post_final grade
Output: d2l_final_COHORT_SEMESTER.csv

Shows grade summary:
- Passing count (≥60%)
- Failing count (<60%)
- Percentages

Ready to import directly into D2L:
1. D2L → Grades → Import
2. Select CSV file
3. Map to final grade column
```

### Query System

The query system can be used programmatically:

#### Student Queries

```python
from queries import StudentQueries

# Lookup by username
student = StudentQueries.get_student_by_username('johndoe', '202580')

# Lookup by org ID
student = StudentQueries.get_student_by_org_id('E00123456', '202580')

# Fuzzy name search
students = StudentQueries.search_students_by_name('Smith', '202580', limit=10)

# Returns dict with all grade information:
{
    'username': 'johndoe',
    'org_defined_id': 'E00123456',
    'first_name': 'John',
    'last_name': 'Doe',
    'email': 'johndoe@etsu.edu',
    'lab_section': 'CSCI-1150-001',
    'lecture_section': 'CSCI-1100-001',
    'lab_average': 87.45,
    'quizzes_average': 92.13,
    'exit_tickets_average': 88.76,
    'dca_score': 95.00,
    'overall_pre_final': 89.23,
    'overall_post_final': 90.12,
    'has_final_project': True,
    # ... more fields
}
```

#### Section Queries

```python
from queries import SectionQueries

# List all sections
sections = SectionQueries.list_available_sections('202580')
# Optional: filter by type
lab_sections = SectionQueries.list_available_sections('202580', course_type='LAB')

# Get lab section grades
students = SectionQueries.get_lab_section_grades('CSCI-1150', '001', '202580')

# Get lecture section grades
students = SectionQueries.get_lecture_section_grades('CSCI-1100', '001', '202580')

# Returns list of student dicts (same format as StudentQueries)
```

#### Cohort Queries

```python
from queries import CohortQueries

# Get all in-person students
inperson = CohortQueries.get_inperson_students('202580')

# Get all online students
online = CohortQueries.get_online_students('202580')

# Get all students (both cohorts)
all_students = CohortQueries.get_all_students('202580')

# Get cohort statistics
stats = CohortQueries.get_cohort_statistics('202580', 'inperson')
# Returns:
{
    'total_students': 885,
    'students_with_dca': 850,
    'students_with_lab': 885,
    'students_with_quizzes': 885,
    'students_with_exit_tickets': 885,
    'avg_lab': 87.45,
    'avg_quizzes': 92.13,
    'avg_exit_tickets': 88.76,
    'avg_dca': 94.23,
    'avg_overall_pre': 89.23,
    'avg_overall_post': 90.12,
    'passing_rate_pre': 91.8,
    'passing_rate_post': 93.2,
    'grade_distribution': {
        'A': 402,
        'B': 310,
        'C': 100,
        'D': 0,
        'F': 73
    }
}
```

#### Formatting

```python
from queries import GradeFormatter

# Format single student
print(GradeFormatter.format_single_student(student))

# Format student list
print(GradeFormatter.format_student_list(students))

# Format section summary
print(GradeFormatter.format_section_summary(students, 'CSCI-1150-001'))

# Format cohort statistics
print(GradeFormatter.format_cohort_statistics(stats, 'inperson'))
```

#### CSV Export

```python
import csv

# Export query results to CSV
students = CohortQueries.get_inperson_students('202580')

with open('inperson_students.csv', 'w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=students[0].keys())
    writer.writeheader()
    writer.writerows(students)
```

---

## Database Schema

### Tables

#### Student
```sql
CREATE TABLE students (
    org_defined_id TEXT PRIMARY KEY,  -- E00123456
    username TEXT UNIQUE NOT NULL,     -- johndoe
    email TEXT,                        -- johndoe@etsu.edu
    first_name TEXT,                   -- John
    last_name TEXT                     -- Doe
);
```

#### Course
```sql
CREATE TABLE courses (
    ou TEXT PRIMARY KEY,               -- 10219691
    course_name TEXT NOT NULL,         -- CSCI-1150
    course_type TEXT NOT NULL,         -- LAB or LECTURE
    section TEXT NOT NULL,             -- 001
    semester TEXT NOT NULL             -- 202580
);
```

#### StudentGrade
Main table storing all grade information for a student in a semester:

```sql
CREATE TABLE student_grades (
    id INTEGER PRIMARY KEY,
    student_id TEXT NOT NULL,          -- FK to students.org_defined_id
    semester TEXT NOT NULL,
    
    -- Lab section relationship
    lab_course_ou TEXT,                -- FK to courses.ou
    lab_numerator REAL,                -- Points earned
    lab_denominator REAL,              -- Points possible
    lab_average REAL,                  -- Percentage
    dca_score REAL,                    -- DCA percentage
    
    -- Lecture section relationship
    lecture_course_ou TEXT,            -- FK to courses.ou
    quizzes_numerator REAL,
    quizzes_denominator REAL,
    quizzes_average REAL,
    exit_tickets_numerator REAL,
    exit_tickets_denominator REAL,
    exit_tickets_average REAL,
    
    -- Calculated overall grades
    overall_grade_pre_final REAL,      -- Before DCA
    overall_grade_post_final REAL,     -- After DCA
    has_final_project BOOLEAN,         -- DCA submitted?

    last_updated TIMESTAMP,

    UNIQUE(student_id, semester)
);
```

#### GradeSnapshot
Historical snapshots of grades at specific points in time:

```sql
CREATE TABLE grade_snapshots (
    id INTEGER PRIMARY KEY,
    student_id TEXT NOT NULL,
    course_ou TEXT NOT NULL,
    snapshot_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Snapshot of all grade components
    lab_numerator REAL,
    lab_denominator REAL,
    lab_average REAL,
    quizzes_numerator REAL,
    quizzes_denominator REAL,
    quizzes_average REAL,
    exit_tickets_numerator REAL,
    exit_tickets_denominator REAL,
    exit_tickets_average REAL,
    dca_score REAL
);
```

### Grade Calculation

Overall grades are calculated automatically using the `calculate_overall_grades()` method:

```python
# Pre-final calculation (before DCA graded)
# Each component (lab, quizzes, exit tickets) has equal weight of 1/3
overall_pre_final = (lab_average + quizzes_average + exit_tickets_average) / 3

# Post-final calculation (after DCA graded)
# Pre-final grade and DCA each worth 50%
overall_post_final = (overall_pre_final + dca_score) / 2
```

### Cohort Determination

Students are assigned to cohorts based on their **lecture section**:

```python
# In-person: lecture sections 001-899
# Online: lecture sections 900+

# Examples:
CSCI-1100-001 → In-person
CSCI-1100-201 → In-person
CSCI-1100-901 → Online
CSCI-1100-940 → Online
```

Lab sections don't determine cohort - only lecture sections.

---

## Troubleshooting

### Database Issues

**Problem: No courses or student grades in database**

```bash
# Check database health
python diagnose_database.py

# If shows 0 courses/grades, reset and re-scrape
cp grades.db grades.db.backup
python -m database.init_db --drop
python scrape.py
```

**Problem: Duplicate students or sections**

```bash
# The database uses UNIQUE constraints, but if data gets corrupted:
python -m database.init_db --drop
python scrape.py
```

### Scraping Issues

**Problem: "bad parameter or other API misuse" SQLite error**

This happens when workers try to save to database in parallel. Fixed by:
- Workers scrape in parallel (no DB access)
- Main thread saves sequentially (safe)

If you see this error, make sure you're using the fixed `scrape.py`.

**Problem: Missing sections or students**

```bash
# Check scraper logs
ls -la scraping/logs/

# Look for errors in most recent log
cat scraping/logs/LabGradesScraper_*.log
cat scraping/logs/LectureGradesScraper_*.log
```

**Problem: Scraping is very slow**

Adjust worker count in `scrape.py`:
```python
# Fewer workers (safer, slower)
num_workers=1

# More workers (faster, more memory)
num_workers=4
```

### Query Issues

**Problem: No results from queries**

Check semester:
```python
# Make sure you're querying the right semester
from database.models import get_current_semester

semester = get_current_semester()
print(f"Current semester: {semester}")

# If wrong, pass semester explicitly
students = CohortQueries.get_inperson_students('202580')
```

**Problem: "KeyError: 'lab_section'" or similar**

Make sure you're using the updated query files:
```bash
# Check that queries/ directory has:
- student_queries.py
- section_queries.py
- cohort_queries.py
- formatting.py
```

### Export Issues

**Problem: "openpyxl not installed"**

```bash
pip install openpyxl --break-system-packages
```

**Problem: Excel workbook looks wrong**

The workbook uses openpyxl styling. If it looks unstyled:
```bash
pip install --upgrade openpyxl --break-system-packages
```

**Problem: D2L won't accept import file**

Make sure:
1. File has `End-of-Line Indicator` column with `#` values
2. Column names match D2L expectations:
   - `ESPR Points Grade` (for midterm)
   - `End-of-Term Points Grade` (for final)
3. File is CSV format (not Excel)

---

## Development

### Project Structure

```
batch_grades/
├── scraping/          # Data collection layer
├── database/          # Data storage layer
├── queries/           # Data access layer
├── workers.py         # Parallel processing
├── scrape.py          # Scraping orchestration
├── cli.py             # User interface
└── test_queries.py    # Testing
```

### Testing

```bash
# Test query system
python test_queries.py -u USERNAME -o ORGID -n "NAME"

# Test specific semester
python test_queries.py -u USERNAME -o ORGID -n "NAME" -s 202610

# Check database health
python diagnose_database.py

# Check specific student
python diagnose_database.py USERNAME
```

### Adding New Features

#### Add a new CLI feature

1. Add method to `CLIActions` class in `cli.py`:
```python
def my_new_feature(self):
    """Description."""
    print("MY NEW FEATURE")
    print("-" * 80)

    # Your implementation
    data = SomeQuery.get_data(self.semester)
    print(GradeFormatter.format_data(data))
    self._offer_export(data, "filename")
```

2. Add menu item in `main()`:
```python
menu.add_item("11", "My new feature", actions.my_new_feature)
```

#### Add a new query

1. Add static method to appropriate class in `queries/`:
```python
@staticmethod
def my_new_query(semester: str) -> List[Dict]:
    """Documentation."""
    db = get_db()
    try:
        # Your query logic
        return results
    finally:
        db.close()
```

2. Add formatter in `queries/formatting.py` if needed
3. Use in CLI or programmatically

### Grade Calculation Logic

Grades are calculated in `database/models.py`:

```python
class StudentGrade(Base):
    # ... fields ...

    def calculate_overall_grades(self):
        """Calculate pre-final and post-final overall grades."""
        # Get component averages
        lab = self.lab_average or 0.0
        quiz = self.quizzes_average or 0.0
        exit_ticket = self.exit_tickets_average or 0.0
        dca = self.dca_score or 0.0

        # Pre-final: average of lab, quizzes, and exit tickets (equal weight: 1/3 each)
        self.overall_grade_pre_final = (lab + quiz + exit_ticket) / 3

        # Post-final: average of pre-final grade and DCA (equal weight: 50% each)
        self.overall_grade_post_final = (self.overall_grade_pre_final + dca) / 2
```

To modify the calculation logic, edit this method in `database/models.py`.

### Semester Detection

Semesters are auto-detected ba
### Data Flow

```
┌──────────────────────────────────────────────────────────────┐
│ SCRAPING PHASE (Phase I)                                     │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  D2L → Scrapers → Workers (Parallel) → CSV Files             │
│                                                              │
│  CSV Files → Main Thread (Sequential) → Database             │
│                                                              │
│  Result: grades.db populated with all student data           │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│ QUERY PHASE (Phase II)                                       │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  User Request → Query System → Database                      │
│                                                              │
│  Database → Query Results → Formatter → Display              │
│                                                              │
│  Result: Formatted output to console                         │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│ EXPORT PHASE (Phase III)                                     │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  User Request → CLI → Query System → Database                │
│                                                              │
│  Database → Query Results → Export Module → File             │
│                                                              │
│  Result: Excel workbook, D2L CSV, or custom export           │
└──────────────────────────────────────────────────────────────┘
```
