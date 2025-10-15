# System Architecture Documentation

Complete architectural overview of the D2L Grades Management System.

## High-Level Architecture

The system follows a **layered architecture** with clear separation of concerns:

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

---

## Data Flow

### Phase I: Data Collection (Scraping)

```
User runs scrape.py
        │
        ▼
┌──────────────────┐
│ 1. OU Discovery  │  Find section identifiers
└──────────────────┘
        │
        ▼
┌──────────────────┐
│ 2. Worker Pool   │  Parallel scraping (no DB access)
│    Distribution  │
└──────────────────┘
        │
        ├─→ Worker 1 scrapes Lab 001-018  → CSV files
        ├─→ Worker 2 scrapes Lab 019-036  → CSV files
        └─→ Worker 3 scrapes Lab 037-054  → CSV files
        │
        ▼
┌──────────────────┐
│ 3. Main Thread   │  Sequential database saves (thread-safe)
│    Saves         │
└──────────────────┘
        │
        ▼
   grades.db populated
```

### Phase II: Data Retrieval (Queries)

```
User query
        │
        ▼
┌──────────────────┐
│  Query Module    │  (Student/Section/Cohort)
└──────────────────┘
        │
        ▼
┌──────────────────┐
│  Database Query  │  SQLAlchemy ORM
└──────────────────┘
        │
        ▼
┌──────────────────┐
│  Result Set      │  List[Dict]
└──────────────────┘
        │
        ▼
┌──────────────────┐
│  Formatter       │  Pretty tables, statistics
└──────────────────┘
        │
        ▼
   Console output
```

### Phase III: Data Export (Reports)

```
User export request
        │
        ▼
┌──────────────────┐
│  CLI Handler     │  Prompts for options
└──────────────────┘
        │
        ▼
┌──────────────────┐
│  Query System    │  Fetch required data
└──────────────────┘
        │
        ▼
┌──────────────────┐
│  Export Module   │  Generate file
└──────────────────┘
        │
        ├─→ D2L CSV (ESPR/Final)
        ├─→ Excel Workbook (56 sheets)
        └─→ Custom CSV
```

---

## Layer Details

### Layer 1: D2L Web Interface
**Purpose:** Source of truth for all grade data

**Characteristics:**
- Web-based LMS (Desire2Learn)
- Requires authentication
- 52 lab sections (CSCI-1150-001 through 909)
- 2 lecture sections (CSCI-1100-001, 901)
- Grade exports available as CSV downloads

**Access Method:**
- Selenium WebDriver automation
- ChromeDriver for browser control
- Session-based authentication

---

### Layer 2: Scraping Layer
**Purpose:** Automated data collection from D2L

**Components:**

#### OUScraper
```python
Responsibility: Discover section identifiers (OUs)
Input: Section ranges
Output: CSV with course names, sections, OUs
```

#### LabGradesScraper
```python
Responsibility: Download lab grade data
Input: Lab section OUs
Output: DataFrames with lab grades, DCA scores
Key Features:
  - Handles missing students
  - Processes lab averages
  - Extracts DCA scores from final project
```

#### LectureGradesScraper
```python
Responsibility: Download lecture grade data
Input: Lecture section OUs
Output: DataFrames with quiz/exit ticket grades
Key Features:
  - Processes multiple grade components
  - Handles weighted categories
  - Maps students to lab sections
```

**Design Pattern:**
- All scrapers inherit from `BaseScraper`
- Template method pattern for common operations
- Configurable for different course structures

---

### Layer 3: Worker Pool
**Purpose:** Parallel processing for performance

**Strategies:**

#### ChunkedWorkerPool
```python
Distribution: Divide sections into equal chunks
Use Case: Balanced workloads
Example: 54 sections, 3 workers → 18 sections each

Benefits:
  - Predictable distribution
  - Easy to reason about
  - Good for uniform section sizes
```

#### RoundRobinWorkerPool
```python
Distribution: Assign sections one-by-one in rotation
Use Case: Variable-sized sections
Example: Section 1→W1, Section 2→W2, Section 3→W3, Section 4→W1...

Benefits:
  - Better load balancing for variable sizes
  - More flexible
  - Good for mixed workloads
```

**Critical Design Decision:**
- Workers scrape in parallel (fast)
- Workers do NOT touch database (safe)
- Main thread saves to database sequentially (no threading issues)

---

### Layer 4: Database Layer
**Purpose:** Persistent storage with relational integrity

**Schema:**

```sql
Student (org_defined_id PK, username, email, first_name, last_name)
    │
    ├─→ StudentGrade (student_id FK, semester, all grade components)
    │       │
    │       ├─→ Course (lab_course_ou FK)
    │       └─→ Course (lecture_course_ou FK)
    │
    └─→ GradeSnapshot (student_id FK, historical data)

Course (ou PK, course_name, section, semester, course_type)
```

**Key Features:**
- SQLite for simplicity (no server required)
- SQLAlchemy ORM for abstraction
- Automatic grade calculations
- Unique constraints prevent duplicates
- Foreign keys enforce referential integrity

**Grade Calculation Logic:**
```python
# Pre-final (before DCA graded)
# Lab, quizzes, and exit tickets each have equal weight (1/3)
overall_pre_final = (lab_average + quizzes_average + exit_tickets_average) / 3

# Post-final (after DCA graded)
# Pre-final grade and DCA each worth 50%
overall_post_final = (overall_pre_final + dca_score) / 2
```

---

### Layer 5: Query System
**Purpose:** Data access abstraction

**Modules:**

#### StudentQueries
```python
Methods:
  - get_student_by_username(username, semester)
  - get_student_by_org_id(org_id, semester)
  - search_students_by_name(name, semester, limit)

Returns: Dict with complete student grade profile
```

#### SectionQueries
```python
Methods:
  - list_available_sections(semester, course_type)
  - get_lab_section_grades(course_name, section, semester)
  - get_lecture_section_grades(course_name, section, semester)

Returns: List[Dict] of all students in section
```

#### CohortQueries
```python
Methods:
  - get_inperson_students(semester)
  - get_online_students(semester)
  - get_all_students(semester)
  - get_cohort_statistics(semester, cohort_type)

Cohort Logic:
  - In-person: lecture section < 900
  - Online: lecture section >= 900

Returns: List[Dict] or statistics dict
```

#### GradeFormatter
```python
Methods:
  - format_single_student(student)
  - format_student_list(students)
  - format_section_summary(students, section_name)
  - format_cohort_statistics(stats, cohort_type)

Output: Formatted tables for console display
```

**Design Principles:**
- Static methods (no state)
- Returns dictionaries (easy to serialize)
- Session management handled internally
- No direct CLI coupling

---

### Layer 6: User Interface Layer
**Purpose:** User interaction and data export

**Components:**

#### CLI Interface (cli.py)
```python
Interactive menu system with 10 features:

Query & View (1-5):
  1. Student lookup
  2. Section grades
  3. Cohort comparison
  4. At-risk students
  5. Missing DCA

Export & Report (6-8):
  6. Lab instructor workbook
  7. D2L ESPR export
  8. D2L final export

Architecture:
  - Menu system with callbacks
  - CLIActions class for feature implementations
  - Prompts for user input
  - Offers CSV exports after queries
```

#### Programmatic API
```python
Direct usage without CLI:

from queries import StudentQueries, CohortQueries

# Lookup student
student = StudentQueries.get_student_by_username('johndoe', '202580')

# Get cohort
students = CohortQueries.get_inperson_students('202580')

# Use for automation scripts
```

#### Export Modules
```python
D2L Exports:
  - ESPR (midterm) grades
  - Final grades
  - D2L-compatible CSV format
  - End-of-Line Indicator column

Excel Export:
  - 56-sheet workbook
  - Professional styling (openpyxl)
  - Lab sections, lecture cohorts, summaries
  - Grade distribution charts
```

---

## Design Decisions

### 1. Sequential Database Saves
**Problem:** SQLite doesn't handle concurrent writes well

**Solution:** Workers scrape in parallel (no DB), main thread saves sequentially

**Benefits:**
- No threading conflicts
- No database locks
- Simple error handling
- Reliable saves

### 2. Query System Abstraction
**Problem:** Direct database access from CLI is messy

**Solution:** Query layer with clean API

**Benefits:**
- Separation of concerns
- Testable independently
- Reusable in other interfaces
- Easy to mock for testing

### 3. Dictionary Returns
**Problem:** ORM objects are hard to serialize/export

**Solution:** Convert to dictionaries in query layer

**Benefits:**
- Easy CSV export
- JSON serializable
- No ORM leakage
- Simple to work with

### 4. Cohort by Lecture Section
**Problem:** Need to group students (in-person vs online)

**Solution:** Use lecture section number (001-899 vs 900+)

**Benefits:**
- Natural grouping
- Easy to query
- Matches institutional structure
- Clear business logic

### 5. Pre-final vs Post-final Grades
**Problem:** Need grades before and after final project (DCA)

**Solution:** Calculate both, store both

**Benefits:**
- Midterm reporting (ESPR)
- Final grade submission
- Progress tracking
- What-if scenarios

---

## Performance Considerations

### Scraping
- **Parallel workers:** 2-4 (configurable)
- **Time:** ~12-16 minutes for full scrape
- **Bottleneck:** Network I/O and D2L page loads

### Database
- **Engine:** SQLite with WAL mode
- **Indexes:** On username, org_defined_id, semester
- **Query time:** <100ms for most queries
- **Size:** ~5-10 MB for 1700 students

### Exports
- **CSV:** Instant (<1 second)
- **Excel:** 30-60 seconds for 56 sheets
- **Memory:** Moderate (loads all data in memory)

---

## 📚 Related Documentation

- **README.md** - Complete usage guide
- **QUICKREF.md** - Quick reference


