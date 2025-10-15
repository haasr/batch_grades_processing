"""
Student-based queries for looking up individual students.

This module provides functionality to look up students by:
- Org Defined ID (exact match)
- Username (exact match)
- Fuzzy name search (partial matching on first/last name)

And retrieve their complete grade profiles.
"""

from typing import List, Dict, Optional
from sqlalchemy import or_, func
from database import get_db, Student, Course, StudentGrade


class StudentQueries:
    """Queries for retrieving individual students and their grades."""
    
    @staticmethod
    def get_student_by_org_id(org_id: str, semester: str) -> Optional[Dict]:
        """
        Get a student and their grades by Org Defined ID.
        
        Args:
            org_id: Student's org defined ID (e.g., 'E00123456')
            semester: Semester code (e.g., '202580')
            
        Returns:
            Dictionary with student info and all grade components, or None if not found
            
        Example:
            >>> student = StudentQueries.get_student_by_org_id('E00123456', '202580')
            >>> if student:
            ...     print(f"{student['username']}: {student['overall_pre_final']}%")
        """
        db = get_db()
        try:
            student = db.query(Student).filter_by(org_defined_id=org_id).first()
            if not student:
                return None

            grade = db.query(StudentGrade).filter_by(
                student_id=org_id,
                semester=semester
            ).first()
            
            if not grade:
                # Student exists but has no grades for this semester
                return StudentQueries._format_student_only(student)
            
            return StudentQueries._format_student_grade(student, grade, db)
            
        finally:
            db.close()
    
    @staticmethod
    def get_student_by_username(username: str, semester: str) -> Optional[Dict]:
        """
        Get a student and their grades by username.
        
        Args:
            username: Student's username (e.g., 'johndoe')
            semester: Semester code (e.g., '202580')
            
        Returns:
            Dictionary with student info and all grade components, or None if not found
            
        Example:
            >>> student = StudentQueries.get_student_by_username('johndoe', '202580')
            >>> if student:
            ...     print(f"{student['first_name']} {student['last_name']}: {student['overall_pre_final']}%")
        """
        db = get_db()
        try:
            student = db.query(Student).filter_by(username=username).first()
            if not student:
                return None

            grade = db.query(StudentGrade).filter_by(
                student_id=student.org_defined_id,
                semester=semester
            ).first()
            
            if not grade:
                # Student exists but has no grades for this semester
                return StudentQueries._format_student_only(student)
            
            return StudentQueries._format_student_grade(student, grade, db)
            
        finally:
            db.close()
    
    @staticmethod
    def search_students_by_name(name_query: str, semester: str,
                               limit: int = 20) -> List[Dict]:
        """
        Search for students by partial name match (fuzzy search).
        
        Searches both first_name and last_name fields case-insensitively.

        Args:
            name_query: Partial name to search for (e.g., 'john', 'doe', 'john doe')
            semester: Semester code (e.g., '202580')
            limit: Maximum number of results to return (default 20)
            
        Returns:
            List of dictionaries with student info and grades, ordered by relevance

        Example:
            >>> students = StudentQueries.search_students_by_name('smith', '202580')
            >>> print(f"Found {len(students)} students matching 'smith'")
            >>> for student in students:
            ...     print(f"{student['first_name']} {student['last_name']}: {student['overall_pre_final']}%")
        """
        db = get_db()
        try:
            # Normalize the query
            query_lower = name_query.lower().strip()

            # Split into parts if multiple words provided
            query_parts = query_lower.split()

            # Build the search query
            if len(query_parts) == 1:
                # Single word - search both first and last name
                search_term = f"%{query_parts[0]}%"
                students = db.query(Student)\
                    .filter(
                        or_(
                            func.lower(Student.first_name).like(search_term),
                            func.lower(Student.last_name).like(search_term)
                        )
                    )\
                    .order_by(Student.last_name, Student.first_name)\
                    .limit(limit)\
                    .all()
            else:
                # Multiple words - try to match first name with first part and last name with remaining
                first_term = f"%{query_parts[0]}%"
                last_term = f"%{' '.join(query_parts[1:])}%"
                students = db.query(Student)\
                    .filter(
                        or_(
                            # Match "first last"
                            (func.lower(Student.first_name).like(first_term) &
                             func.lower(Student.last_name).like(last_term)),
                            # Match "last first" (reversed)
                            (func.lower(Student.last_name).like(first_term) &
                             func.lower(Student.first_name).like(last_term)),
                            # Match all parts in either field
                            func.lower(Student.first_name).like(f"%{query_lower}%"),
                            func.lower(Student.last_name).like(f"%{query_lower}%")
                        )
                    )\
                    .order_by(Student.last_name, Student.first_name)\
                    .limit(limit)\
                    .all()

            # Get grades for each student
            results = []
            for student in students:
                grade = db.query(StudentGrade).filter_by(
                    student_id=student.org_defined_id,
                    semester=semester
                ).first()

                if grade:
                    results.append(StudentQueries._format_student_grade(student, grade, db))
                else:
                    results.append(StudentQueries._format_student_only(student))

            return results

        finally:
            db.close()

    @staticmethod
    def get_all_students_info(semester: str) -> List[Dict]:
        """
        Get basic info for all students (without grades).
        
        Useful for getting a list of all students in the system.

        Args:
            semester: Semester code (e.g., '202580')

        Returns:
            List of dictionaries with basic student information
        """
        db = get_db()
        try:
            students = db.query(Student)\
                .order_by(Student.last_name, Student.first_name)\
                .all()

            return [StudentQueries._format_student_only(student) for student in students]

        finally:
            db.close()
    
    @staticmethod
    def _format_student_grade(student: Student, grade: StudentGrade, db) -> Dict:
        """
        Format student and grade information into a dictionary with section info.
        """
        # Get lab section name
        lab_section = None
        if grade.lab_course_ou:
            lab_course = db.query(Course).filter_by(ou=grade.lab_course_ou).first()
            if lab_course:
                lab_section = f"{lab_course.course_name}-{lab_course.section}"
        
        # Get lecture section name
        lecture_section = None
        if grade.lecture_course_ou:
            lecture_course = db.query(Course).filter_by(ou=grade.lecture_course_ou).first()
            if lecture_course:
                lecture_section = f"{lecture_course.course_name}-{lecture_course.section}"
        
        return {
            # Student information
            'org_defined_id': student.org_defined_id,
            'username': student.username,
            'email': student.email,
            'first_name': student.first_name,
            'last_name': student.last_name,
            
            # Section information
            'lab_section': lab_section,
            'lecture_section': lecture_section,
            
            # Lab grades
            'lab_course_ou': grade.lab_course_ou,
            'lab_numerator': grade.lab_numerator or 0.0,
            'lab_denominator': grade.lab_denominator or 0.0,
            'lab_average': grade.lab_average or 0.0,
            'dca_score': grade.dca_score or 0.0,
            
            # Lecture grades
            'lecture_course_ou': grade.lecture_course_ou,
            'quizzes_numerator': grade.quizzes_numerator or 0.0,
            'quizzes_denominator': grade.quizzes_denominator or 0.0,
            'quizzes_average': grade.quizzes_average or 0.0,
            'exit_tickets_numerator': grade.exit_tickets_numerator or 0.0,
            'exit_tickets_denominator': grade.exit_tickets_denominator or 0.0,
            'exit_tickets_average': grade.exit_tickets_average or 0.0,
            
            # Overall grades
            'overall_pre_final': grade.overall_grade_pre_final or 0.0,
            'overall_post_final': grade.overall_grade_post_final or 0.0,
            'has_final_project': grade.has_final_project,
            
            # Metadata
            'semester': grade.semester,
            'last_updated': grade.last_updated,
        }
    
    @staticmethod
    def _format_student_only(student: Student) -> Dict:
        """
        Format student information only (no grades).
        
        Used when a student exists but has no grade records for the semester.
        """
        return {
            # Student information
            'org_defined_id': student.org_defined_id,
            'username': student.username,
            'email': student.email,
            'first_name': student.first_name,
            'last_name': student.last_name,
            
            # Section information
            'lab_section': None,
            'lecture_section': None,
            
            # Lab grades (all None/0)
            'lab_course_ou': None,
            'lab_numerator': 0.0,
            'lab_denominator': 0.0,
            'lab_average': 0.0,
            'dca_score': 0.0,
            
            # Lecture grades (all None/0)
            'lecture_course_ou': None,
            'quizzes_numerator': 0.0,
            'quizzes_denominator': 0.0,
            'quizzes_average': 0.0,
            'exit_tickets_numerator': 0.0,
            'exit_tickets_denominator': 0.0,
            'exit_tickets_average': 0.0,
            
            # Overall grades (all None/0)
            'overall_pre_final': 0.0,
            'overall_post_final': 0.0,
            'has_final_project': False,

            # Metadata
            'semester': None,
            'last_updated': None,
        }
