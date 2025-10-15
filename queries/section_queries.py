"""
Section-based queries for retrieving all students in a specific course section.

This module provides functionality to look up all students enrolled in:
- A specific lab section (e.g., CSCI-1150-001)
- A specific lecture section (e.g., CSCI-1100-901)

And retrieve their complete grade profiles including lab, lecture, and overall grades.
"""

from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from database import get_db, Student, Course, StudentGrade


class SectionQueries:
    """Queries for retrieving students by course section."""
    
    @staticmethod
    def get_lab_section_grades(course_name: str, section: str, semester: str) -> List[Dict]:
        """
        Get all students and their grades for a specific lab section.
        
        Args:
            course_name: Course name without section (e.g., 'CSCI-1150')
            section: Three-digit section code (e.g., '001', '901')
            semester: Semester code (e.g., '202580')
            
        Returns:
            List of dictionaries containing student info and all grade components
            
        Example:
            >>> results = SectionQueries.get_lab_section_grades('CSCI-1150', '001', '202580')
            >>> for student in results:
            ...     print(f"{student['username']}: {student['overall_pre_final']}%")
        """
        db = get_db()
        try:
            # Find the course OU for this section
            course = db.query(Course).filter_by(
                course_name=course_name,
                section=section,
                semester=semester,
                course_type='LAB'
            ).first()
            
            if not course:
                return []
            
            # Get all students with grades for this lab section
            results = db.query(Student, StudentGrade)\
                .join(StudentGrade, Student.org_defined_id == StudentGrade.student_id)\
                .filter(StudentGrade.lab_course_ou == course.ou)\
                .filter(StudentGrade.semester == semester)\
                .all()
            
            return [SectionQueries._format_student_grade(student, grade, db) for student, grade in results]
            
        finally:
            db.close()
    
    @staticmethod
    def get_lecture_section_grades(course_name: str, section: str, semester: str) -> List[Dict]:
        """
        Get all students and their grades for a specific lecture section.
        
        Args:
            course_name: Course name without section (e.g., 'CSCI-1100')
            section: Three-digit section code (e.g., '001', '901')
            semester: Semester code (e.g., '202580')
            
        Returns:
            List of dictionaries containing student info and all grade components
            
        Example:
            >>> results = SectionQueries.get_lecture_section_grades('CSCI-1100', '901', '202580')
            >>> for student in results:
            ...     print(f"{student['last_name']}, {student['first_name']}: {student['quizzes_average']}%")
        """
        db = get_db()
        try:
            # Find the course OU for this section
            course = db.query(Course).filter_by(
                course_name=course_name,
                section=section,
                semester=semester,
                course_type='LECTURE'
            ).first()
            
            if not course:
                return []
            
            # Get all students with grades for this lecture section
            results = db.query(Student, StudentGrade)\
                .join(StudentGrade, Student.org_defined_id == StudentGrade.student_id)\
                .filter(StudentGrade.lecture_course_ou == course.ou)\
                .filter(StudentGrade.semester == semester)\
                .all()
            
            return [SectionQueries._format_student_grade(student, grade, db) for student, grade in results]
            
        finally:
            db.close()
    
    @staticmethod
    def get_section_grades(course_name: str, section: str, semester: str, 
                          course_type: Optional[str] = None) -> List[Dict]:
        """
        Convenience method that automatically determines if section is LAB or LECTURE.
        
        Args:
            course_name: Course name (e.g., 'CSCI-1150' or 'CSCI-1100')
            section: Three-digit section code (e.g., '001', '901')
            semester: Semester code (e.g., '202580')
            course_type: Optional. If not provided, infers from course_name
            
        Returns:
            List of dictionaries containing student info and all grade components
        """
        # Infer course type from course name if not provided
        if course_type is None:
            if '1150' in course_name:
                course_type = 'LAB'
            elif '1100' in course_name:
                course_type = 'LECTURE'
            else:
                # Try both if we can't determine
                lab_results = SectionQueries.get_lab_section_grades(course_name, section, semester)
                if lab_results:
                    return lab_results
                return SectionQueries.get_lecture_section_grades(course_name, section, semester)
        
        if course_type.upper() == 'LAB':
            return SectionQueries.get_lab_section_grades(course_name, section, semester)
        else:
            return SectionQueries.get_lecture_section_grades(course_name, section, semester)
    
    @staticmethod
    def _format_student_grade(student: Student, grade: StudentGrade, db) -> Dict:
        """
        Format student and grade information into a dictionary with section info.
        
        Returns a dictionary with all student info, grade components, and section names.
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
    def list_available_sections(semester: str, course_type: Optional[str] = None) -> List[Dict]:
        """
        List all available course sections for a given semester.
        
        Args:
            semester: Semester code (e.g., '202580')
            course_type: Optional filter for 'LAB' or 'LECTURE'
            
        Returns:
            List of dictionaries with course information
            
        Example:
            >>> sections = SectionQueries.list_available_sections('202580', 'LAB')
            >>> for section in sections:
            ...     print(f"{section['course_name']}-{section['section']}")
        """
        db = get_db()
        try:
            query = db.query(Course).filter_by(semester=semester)
            
            if course_type:
                query = query.filter_by(course_type=course_type.upper())
            
            courses = query.order_by(Course.course_name, Course.section).all()
            
            return [{
                'ou': course.ou,
                'course_name': course.course_name,
                'section': course.section,
                'course_type': course.course_type,
                'semester': course.semester,
            } for course in courses]
            
        finally:
            db.close()
