"""
Test script for the query layer.

Run this to verify that queries work correctly before building the GUI.
"""

from queries import StudentQueries, SectionQueries, CohortQueries
from queries.formatting import GradeFormatter
from database.models import get_current_semester

CURRENT_SEMESTER = get_current_semester()

def test_student_queries(username: str, org_defined_id: str, name='', semester=CURRENT_SEMESTER):
    """Test individual student lookups."""
    print("\n" + "="*80)
    print("TESTING STUDENT QUERIES")
    print("="*80)
    
    # Test by username
    print("\n1. Testing lookup by username...")
    student = StudentQueries.get_student_by_username(username, semester)
    if student:
        print(GradeFormatter.format_single_student(student))
    else:
        print(f"No student found with username '{username}'")
    
    # Test by org ID
    print("\n2. Testing lookup by Org ID...")
    student = StudentQueries.get_student_by_org_id(f"{org_defined_id}", semester)
    if student:
        print(GradeFormatter.format_single_student(student))
    else:
        print(f"No student found with Org ID '{org_defined_id}'")
    
    # Test fuzzy name search
    print("\n3. Testing fuzzy name search...")
    students = StudentQueries.search_students_by_name(name, semester, limit=5)
    if students:
        print(f"✓ Found {len(students)} students matching '{name}':")
        print(GradeFormatter.format_student_list(students))
    else:
        print(f"No students found matching '{name}'")

def test_section_queries(semester=CURRENT_SEMESTER):
    """Test section-based lookups."""
    print("\n" + "="*80)
    print("TESTING SECTION QUERIES")
    print("="*80)
    
    # List available sections
    print("\n1. Listing available sections...")
    sections = SectionQueries.list_available_sections(semester)
    if sections:
        print(f"✓ Found {len(sections)} sections:")
        for section in sections[:10]:  # Show first 10
            print(f"  {section['course_name']}-{section['section']} ({section['course_type']}) - OU: {section['ou']}")
        if len(sections) > 10:
            print(f"  ... and {len(sections) - 10} more")
    else:
        print("No sections found")
    
    # Test lab section lookup
    if sections:
        print("\n2. Testing lab section lookup...")
        lab_sections = [s for s in sections if s['course_type'] == 'LAB']
        if lab_sections:
            test_section = lab_sections[0]
            students = SectionQueries.get_lab_section_grades(
                test_section['course_name'],
                test_section['section'],
                semester
            )
            if students:
                section_name = f"{test_section['course_name']}-{test_section['section']}"
                print(GradeFormatter.format_section_summary(students, section_name))
            else:
                print(f"No students found in {test_section['course_name']}-{test_section['section']}")
        else:
            print("No lab sections found")
    
    # Test lecture section lookup
    if sections:
        print("\n3. Testing lecture section lookup...")
        lecture_sections = [s for s in sections if s['course_type'] == 'LECTURE']
        if lecture_sections:
            test_section = lecture_sections[0]
            students = SectionQueries.get_lecture_section_grades(
                test_section['course_name'],
                test_section['section'],
                semester
            )
            if students:
                section_name = f"{test_section['course_name']}-{test_section['section']}"
                print(GradeFormatter.format_section_summary(students, section_name))
            else:
                print(f"No students found in {test_section['course_name']}-{test_section['section']}")
        else:
            print("No lecture sections found")

def test_cohort_queries(semester=CURRENT_SEMESTER):
    """Test cohort-based lookups."""
    print("\n" + "="*80)
    print("TESTING COHORT QUERIES")
    print("="*80)
    
    # Test in-person cohort
    print("\n1. Testing in-person cohort...")
    inperson = CohortQueries.get_inperson_students(semester)
    if inperson:
        print(f"Found {len(inperson)} in-person students")
        print("\nFirst 10 in-person students:")
        print(GradeFormatter.format_student_list(inperson[:10]))
        
        print("\n" + "-"*80)
        stats = CohortQueries.get_cohort_statistics(semester, 'inperson')
        print(GradeFormatter.format_cohort_statistics(stats, 'inperson'))
    else:
        print("No in-person students found")
    
    # Test online cohort
    print("\n2. Testing online cohort...")
    online = CohortQueries.get_online_students(semester)
    if online:
        print(f"Found {len(online)} online students")
        print("\nFirst 10 online students:")
        print(GradeFormatter.format_student_list(online[:10]))
        
        print("\n" + "-"*80)
        stats = CohortQueries.get_cohort_statistics(semester, 'online')
        print(GradeFormatter.format_cohort_statistics(stats, 'online'))
    else:
        print("No online students found")

import argparse

def main():
    semester = CURRENT_SEMESTER # Defaults to current semester if argument not supplied
    """Run all tests."""
    parser = argparse.ArgumentParser(description="Run query layer tests.")

    # Required arguments (use 'required=True')
    parser.add_argument("-u", "--username", required=True, help="Test username")
    parser.add_argument("-o", "--org_defined_id", required=True, help="Test org_defined_id")
    parser.add_argument("-n", "--name", required=True, help="Test name (first, last, or both)")

    # Optional argument
    parser.add_argument("-s", "--semester", help="Semester code (e.g., 202580 for Fall 2025)")

    args = parser.parse_args()

    username = args.username
    org_defined_id = args.org_defined_id
    name = args.name

    # Use provided semester or fall back to default
    if args.semester: semester = args.semester

    print("\n")
    print("#" * 80)
    print("# QUERY LAYER TEST SUITE")
    print(f"# Testing semester: {semester}")
    print("#" * 80)
    
    try:
        # Test each query type
        test_cohort_queries(semester)
        test_section_queries(semester)
        test_student_queries(username, org_defined_id, name, semester)
        
        print("\n" + "#" * 80)
        print("# ALL TESTS COMPLETED")
        print("#" * 80)
        print("\nIf you see data above, the query layer is working!")
        print("If you see 'No students/sections found', make sure you've run scrape.py first.")
        
    except Exception as e:
        print(f"\n✗ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()