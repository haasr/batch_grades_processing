#!/usr/bin/env python3
"""
D2L Student Information Lookup - GA Edition

A simplified CLI for looking up student information (usernames, emails, sections)
without displaying grade information. Perfect for GAs and staff who need to find
students but don't have access to grade data.
"""

import sys
from typing import Optional
from queries import StudentQueries
from database.models import get_current_semester

# Default semester - can be overridden
CURRENT_SEMESTER = get_current_semester()


class StudentInfoFormatter:
    """Formats student information without grade data."""
    
    @staticmethod
    def format_student_info(student: dict) -> str:
        """Format a single student's basic information."""
        lines = []
        lines.append("=" * 80)
        lines.append("STUDENT INFORMATION")
        lines.append("=" * 80)
        lines.append("")
        
        # Personal Information
        lines.append("Personal Information:")
        lines.append(f"  Name:              {student['first_name']} {student['last_name']}")
        lines.append(f"  Username:          {student['username']}")
        lines.append(f"  Email:             {student['email']}")
        lines.append(f"  Org Defined ID:    {student['org_defined_id']}")
        lines.append("")
        
        # Section Information
        lines.append("Section Enrollment:")
        lines.append(f"  Lab Section:       {student['lab_section'] or 'Not enrolled'}")
        lines.append(f"  Lecture Section:   {student['lecture_section'] or 'Not enrolled'}")
        lines.append("")
        
        lines.append("=" * 80)
        return "\n".join(lines)
    
    @staticmethod
    def format_student_list(students: list) -> str:
        """Format a list of students as a simple table."""
        if not students:
            return "No students found."
        
        lines = []
        lines.append("=" * 100)
        lines.append(f"{'Name':<25} {'Username':<15} {'OrgId':<10} {'Lecture':<10} {'Lab Section':<15}")
        lines.append("=" * 100)
        
        for student in students:
            name = f"{student['last_name']}, {student['first_name']}"
            lab = student['lab_section'] or 'N/A'
            if student['lecture_section']:
                lecture = student['lecture_section']
                # 001 = in-person, 901 = online
                lecture = 'In-person' if '001' in lecture else 'Online'
            else:
                lecture = 'N/A'

            lines.append(
                f"{name:<25} "
                f"{student['username']:<15} "
                f"{student['org_defined_id']:<10}"
                f"{lecture:<10}"
                f"{lab:<15} "
            )
        
        lines.append("=" * 100)
        lines.append(f"\nTotal: {len(students)} students")
        return "\n".join(lines)


class GAActions:
    """Actions available to GAs (student lookup only)."""
    
    def __init__(self, semester: str):
        self.semester = semester
    
    def lookup_student(self):
        """Look up a student by username, org ID, or name."""
        print("\nSTUDENT LOOKUP")
        print("-" * 80)
        print("\nSearch by:")
        print("  1. Username (exact match)")
        print("  2. Org Defined ID (exact match)")
        print("  3. Name (fuzzy search - first, last, or both)")
        print("  0. Cancel")
        
        choice = input("\nEnter choice (1-3): ").strip()
        
        if choice == "0":
            return
        elif choice == "1":
            username = input("Enter username: ").strip()
            if not username:
                print("✗ Username cannot be empty")
                return
            
            student = StudentQueries.get_student_by_username(username, self.semester)
            if student:
                print("\n" + StudentInfoFormatter.format_student_info(student))
            else:
                print(f"\n✗ No student found with username '{username}'")
        
        elif choice == "2":
            org_id = input("Enter Org Defined ID: ").strip()
            if not org_id:
                print("✗ Org ID cannot be empty")
                return
            
            student = StudentQueries.get_student_by_org_id(org_id, self.semester)
            if student:
                print("\n" + StudentInfoFormatter.format_student_info(student))
            else:
                print(f"\n✗ No student found with Org ID '{org_id}'")
        
        elif choice == "3":
            name = input("Enter name (first, last, or both): ").strip()
            if not name:
                print("✗ Name cannot be empty")
                return
            
            limit = input("Maximum results (default 15): ").strip()
            try:
                limit = int(limit) if limit else 15
            except ValueError:
                limit = 15
            
            students = StudentQueries.search_students_by_name(name, self.semester, limit=limit)
            if students:
                print(f"\n✓ Found {len(students)} students matching '{name}':")
                print(StudentInfoFormatter.format_student_list(students))
            else:
                print(f"\n✗ No students found matching '{name}'")
        
        else:
            print("✗ Invalid choice")
    
    def list_by_section(self):
        """List all students in a specific section."""
        print("\nLIST STUDENTS BY SECTION")
        print("-" * 80)
        print("\nEnter section information:")
        
        course_name = input("Course name (e.g., CSCI-1150): ").strip().upper()
        if not course_name:
            print("✗ Course name cannot be empty")
            return
        
        section = input("Section number (e.g., 001, 901): ").strip()
        if not section:
            print("✗ Section number cannot be empty")
            return
        
        # Pad section to 3 digits
        section = section.zfill(3)
        
        print(f"\nSearching for students in {course_name}-{section}...")
        
        # Import here to avoid circular dependency
        from queries import SectionQueries
        
        # Try lab section first
        students = SectionQueries.get_lab_section_grades(course_name, section, self.semester)
        
        # If no lab students, try lecture
        if not students:
            students = SectionQueries.get_lecture_section_grades(course_name, section, self.semester)
        
        if students:
            print(f"\n✓ Found {len(students)} students in {course_name}-{section}:")
            print(StudentInfoFormatter.format_student_list(students))
        else:
            print(f"\n✗ No students found in {course_name}-{section}")
            print("   Make sure the course name and section number are correct.")


class Menu:
    """Simple menu system."""
    
    def __init__(self):
        self.items = []
    
    def add_item(self, key: str, label: str, action):
        self.items.append((key, label, action))
    
    def display(self):
        print("\n" + "=" * 80)
        print("D2L STUDENT INFORMATION LOOKUP - GA EDITION")
        print("=" * 80)
        print("\nAvailable Options:")
        for key, label, _ in self.items:
            if key == "0":
                print(f"\n  {key}. {label}")
            else:
                print(f"  {key}. {label}")
    
    def run(self):
        while True:
            self.display()
            choice = input("\nEnter your choice: ").strip()
            
            # Find matching action
            action = None
            for key, label, act in self.items:
                if key == choice:
                    action = act
                    break
            
            if action:
                if choice == "0":
                    print("\nGoodbye!")
                    sys.exit(0)
                else:
                    try:
                        action()
                    except KeyboardInterrupt:
                        print("\n\n⚠️  Operation cancelled by user")
                    except Exception as e:
                        print(f"\n✗ Error: {str(e)}")
                        import traceback
                        traceback.print_exc()
                    
                    input("\nPress Enter to continue...")
            else:
                print(f"\n✗ Invalid choice: {choice}")
                input("Press Enter to continue...")


def main(semester: Optional[str] = None):
    """Main entry point."""
    if semester is None:
        semester = CURRENT_SEMESTER
    
    # Validate semester format
    if not semester or len(semester) != 6 or not semester.isdigit():
        print(f"✗ Invalid semester format: {semester}")
        print("   Expected format: YYYYSS (e.g., 202580 for Fall 2025)")
        sys.exit(1)
    
    print("\n" + "=" * 80)
    print("D2L STUDENT INFORMATION LOOKUP - GA EDITION")
    print("=" * 80)
    print(f"\nSemester: {semester}")
    print("\nNOTE: This tool provides student contact and enrollment information only.")
    print("      Grade information is not available in this version.")
    print("=" * 80)
    
    # Create actions
    actions = GAActions(semester)
    
    # Build menu
    menu = Menu()
    menu.add_item("1", "⌕ Lookup student (username, ID, or name)", actions.lookup_student)
    menu.add_item("2", "§ List students by section", actions.list_by_section)
    menu.add_item("0", "Exit", lambda: None)
    
    # Run menu loop
    try:
        menu.run()
    except KeyboardInterrupt:
        print("\n\nGoodbye!")
        sys.exit(0)


if __name__ == '__main__':
    # Check for semester argument
    if len(sys.argv) > 1:
        semester = sys.argv[1]
        main(semester)
    else:
        main()