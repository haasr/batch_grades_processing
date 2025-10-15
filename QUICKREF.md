# Quick Reference Guide

## 🚀 Common Commands

### Daily Usage

```bash
# Launch CLI
python cli.py

# Check database health
python diagnose_database.py

# Test queries
python test_queries.py -u USERNAME -o ORGID -n "NAME"
```

### Scraping

```bash
# Full scrape workflow
python scrape.py

# Fresh start (reset database)
cp grades.db grades.db.backup
python -m database.init_db --drop
python scrape.py
```

### Exports

```bash
# Via CLI (recommended)
python cli.py
# Then select option 6, 7, or 8

# Programmatic export
python -c "from cli import CLIActions; CLIActions('202580').export_d2l_final()"
```

---

## 📊 CLI Menu Quick Reference

| # | Feature | Description | Output |
|---|---------|-------------|--------|
| 1 | Lookup student | Search by username/ID/name | Console + optional CSV |
| 2 | View section | Show all students in section | Console + optional CSV |
| 3 | Compare cohorts | In-person vs online stats | Console + optional CSV |
| 4 | At-risk students | Find failing students | Console + optional CSV |
| 5 | Missing DCA | Students without final project | Console + optional CSV |
| 6 | Lab workbook | 56-sheet Excel file | `.xlsx` file |
| 7 | ESPR export | Midterm grades for D2L | `.csv` file |
| 8 | Final export | Final grades for D2L | `.csv` file |

---

## 💻 Query System Cheat Sheet

### Student Lookups

```python
from queries import StudentQueries

# By username
student = StudentQueries.get_student_by_username('johndoe', '202580')

# By org ID
student = StudentQueries.get_student_by_org_id('E00123456', '202580')

# Fuzzy search
students = StudentQueries.search_students_by_name('Smith', '202580')
```

### Section Queries

```python
from queries import SectionQueries

# List sections
sections = SectionQueries.list_available_sections('202580')
lab_sections = SectionQueries.list_available_sections('202580', 'LAB')

# Get section grades
students = SectionQueries.get_lab_section_grades('CSCI-1150', '001', '202580')
students = SectionQueries.get_lecture_section_grades('CSCI-1100', '001', '202580')
```

### Cohort Queries

```python
from queries import CohortQueries

# Get cohorts
inperson = CohortQueries.get_inperson_students('202580')
online = CohortQueries.get_online_students('202580')
all_students = CohortQueries.get_all_students('202580')

# Get statistics
stats = CohortQueries.get_cohort_statistics('202580', 'inperson')
```

### Formatting

```python
from queries import GradeFormatter

# Format output
GradeFormatter.format_single_student(student)
GradeFormatter.format_student_list(students)
GradeFormatter.format_section_summary(students, 'CSCI-1150-001')
GradeFormatter.format_cohort_statistics(stats, 'inperson')
```

---

## 🗄️ Database Quick Reference

### Table Overview

| Table | Purpose | Key Fields |
|-------|---------|------------|
| `students` | Student info | org_defined_id (PK), username, email |
| `courses` | Section info | ou (PK), course_name, section, semester |
| `student_grades` | Current grades | student_id, semester, all grade fields |
| `grade_snapshots` | Historical grades | student_id, course_ou, snapshot_date |

### Key Relationships

```
Student 1───┐
            ├──→ StudentGrade ───┬──→ Course (lab)
            │                     └──→ Course (lecture)
            └──→ GradeSnapshot
```

### Important Constraints

- `students.org_defined_id`: PRIMARY KEY
- `students.username`: UNIQUE
- `courses.ou`: PRIMARY KEY
- `student_grades(student_id, semester)`: UNIQUE
- All foreign keys cascade on delete

---

## 🔧 Troubleshooting Quick Fixes

### Database Problems

```bash
# Reset everything
python -m database.init_db --drop
python scrape.py

# Check health
python diagnose_database.py
python diagnose_database.py USERNAME
```

### Scraping Errors

```bash
# Check logs
ls -la scraping/logs/
tail -50 scraping/logs/LabGradesScraper_*.log

# Reduce workers if crashing
# Edit scrape.py: num_workers=1
```

### Query Errors

```python
# Check semester
from database.models import get_current_semester
print(get_current_semester())

# Use explicit semester
students = CohortQueries.get_inperson_students('202580')
```

### Import Errors

```bash
# Missing openpyxl
pip install openpyxl --break-system-packages

# Missing other packages
pip install selenium pandas sqlalchemy --break-system-packages
```

---

## 📁 File Locations

### Input Files
- `labs_ou_202580.csv` - Lab section OUs
- `lectures_ou_202580.csv` - Lecture section OUs

### Output Files
- `grades.db` - Main database
- `lab_workbook_202580.xlsx` - Lab instructor workbook
- `d2l_espr_COHORT_202580.csv` - ESPR grades export
- `d2l_final_COHORT_202580.csv` - Final grades export
- `*.csv` - Various query exports

### Log Files
- `scraping/logs/LabGradesScraper_*.log`
- `scraping/logs/LectureGradesScraper_*.log`
- `scraping/logs/OUScraper_*.log`

### Downloaded Data
- `scraping/downloads/lab_grades/*.csv`
- `scraping/downloads/lecture_grades/*.csv`

---

## ⚙️ Configuration

### Semester Codes
```python
# Format: YEAR + CODE
'202580'  # Fall 2025
'202610'  # Spring 2026
'202650'  # Summer 2026
```

### Grade Weights
```python
# Pre-final (before DCA graded)
# Lab, quizzes, and exit tickets each have equal weight (1/3)
overall_pre_final = (lab + quiz + exit_ticket) / 3

# Post-final (after DCA graded)  
# Pre-final grade and DCA each worth 50%
overall_post_final = (overall_pre_final + dca) / 2
```

### Section Ranges
```python
# In-person labs
001-042  # Regular sections
940-942  # Special sections

# Online labs
901-909  # Online sections

# Lectures
001      # In-person
901      # Online
```

---

## Best Practices

### Scraping
1. Run during off-peak hours
2. Start with fresh database each semester
3. Check logs for errors immediately
4. Backup database before re-scraping

### Querying
1. Always specify semester explicitly
2. Use CLI for ad-hoc queries
3. Use programmatic API for automation
4. Export results before complex filtering

### Exporting
1. Test with small cohorts first
2. Verify D2L import format before full export
3. Keep backups of export files
4. Document any custom modifications

### Database
1. Backup before major operations
2. Run diagnostics regularly
3. Clean up old semesters periodically
4. Monitor database size

---

## Typical Workflows

### Start of Semester
```bash
# 1. Initialize fresh database
python -m database.init_db --drop

# 2. Find course OUs
python scrape.py  # Run OU scraping only

# 3. Full scrape
python scrape.py  # Full workflow

# 4. Verify
python diagnose_database.py
```

### Mid-Semester Check
```bash
# 1. Launch CLI
python cli.py

# 2. Find at-risk students (Mode 1: Pre-final)
# Select option 4, choose mode 1

# 3. Export list
# Choose to export CSV

# 4. Follow up with students
```

### End of Semester
```bash
# 1. Final scrape
python scrape.py

# 2. Generate lab workbook
python cli.py
# Select option 6

# 3. Export final grades
python cli.py
# Select option 8

# 4. Import to D2L
# Use generated CSV file
```

---

## Quick Diagnostics

### Is everything working?
```bash
python test_queries.py -u USERNAME -o ORGID -n "NAME"
# Should show sections, cohorts, and student data
```

### Database looks wrong?
```bash
python diagnose_database.py
# Shows counts and identifies problems
```

### Scraping failed?
```bash
ls -la scraping/logs/
# Check most recent log file
```

### Queries return nothing?
```python
from database.models import get_current_semester
print(get_current_semester())
# Verify correct semester
```

---

## 💡 Pro Tips

1. **Bookmark this guide** - You'll reference it often!

2. **Use tab completion** - Most commands support it

3. **Check logs first** - Most errors are logged with details

4. **Test with small sets** - Use `limit=5` when testing queries

5. **Export early, export often** - Don't lose data

6. **Keep backups** - Database and export files

7. **Document modifications** - If you change grade weights, etc.

8. **Use the CLI for exploration** - Programmatic API for automation

## 📚 Related Documentation
- **README.md** - Complete usage guide
- **ARCHITECTURE.md** - Architecture details
