"""
Cohort-based queries for retrieving students by enrollment type.

This module provides functionality to query students based on their enrollment cohort:
- In-person students (lecture sections NOT starting with '9')
- Online students (lecture sections starting with '9')

Cohorts are determined by lecture section numbers:
- In-person: Sections 001-899 (e.g., CSCI-1100-001, CSCI-1100-201)
- Online: Sections 900+ (e.g., CSCI-1100-901, CSCI-1100-940)
"""

from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_
from database import get_db, Student, Course, StudentGrade


class CohortQueries:
    """Queries for retrieving students by enrollment cohort (in-person vs online)."""
    
    @staticmethod
    def get_inperson_students(semester: str) -> List[Dict]:
        """
        Get all students enrolled in in-person lecture sections.
        
        In-person sections are identified by section codes that do NOT start with '9'.
        Examples: CSCI-1100-001, CSCI-1100-002, CSCI-1100-201
        
        Args:
            semester: Semester code (e.g., '202580')
            
        Returns:
            List of dictionaries containing student info and all grade components
            
        Example:
            >>> students = CohortQueries.get_inperson_students('202580')
            >>> print(f"Found {len(students)} in-person students")
            >>> for student in students[:5]:
            ...     print(f"{student['username']}: {student['overall_pre_final']}%")
        """
        db = get_db()
        try:
            # Get all lecture courses for this semester that are in-person
            # In-person sections do NOT start with '9'
            lecture_courses = db.query(Course)\
                .filter_by(semester=semester, course_type='LECTURE')\
                .filter(~Course.section.startswith('9'))\
                .all()
            
            if not lecture_courses:
                return []
            
            # Get all lecture course OUs
            lecture_ous = [course.ou for course in lecture_courses]
            
            # Get all students enrolled in these lecture sections
            results = db.query(Student, StudentGrade)\
                .join(StudentGrade, Student.org_defined_id == StudentGrade.student_id)\
                .filter(StudentGrade.lecture_course_ou.in_(lecture_ous))\
                .filter(StudentGrade.semester == semester)\
                .order_by(Student.last_name, Student.first_name)\
                .all()
            
            return [CohortQueries._format_student_grade(student, grade, db) 
                    for student, grade in results]
            
        finally:
            db.close()
    
    @staticmethod
    def get_online_students(semester: str) -> List[Dict]:
        """
        Get all students enrolled in online lecture sections.
        
        Online sections are identified by section codes that start with '9'.
        Examples: CSCI-1100-901, CSCI-1100-940
        
        Args:
            semester: Semester code (e.g., '202580')
            
        Returns:
            List of dictionaries containing student info and all grade components
            
        Example:
            >>> students = CohortQueries.get_online_students('202580')
            >>> print(f"Found {len(students)} online students")
            >>> for student in students[:5]:
            ...     print(f"{student['username']}: {student['overall_pre_final']}%")
        """
        db = get_db()
        try:
            # Get all lecture courses for this semester that are online
            # Online sections start with '9'
            lecture_courses = db.query(Course)\
                .filter_by(semester=semester, course_type='LECTURE')\
                .filter(Course.section.startswith('9'))\
                .all()
            
            if not lecture_courses:
                return []
            
            # Get all lecture course OUs
            lecture_ous = [course.ou for course in lecture_courses]
            
            # Get all students enrolled in these lecture sections
            results = db.query(Student, StudentGrade)\
                .join(StudentGrade, Student.org_defined_id == StudentGrade.student_id)\
                .filter(StudentGrade.lecture_course_ou.in_(lecture_ous))\
                .filter(StudentGrade.semester == semester)\
                .order_by(Student.last_name, Student.first_name)\
                .all()
            
            return [CohortQueries._format_student_grade(student, grade, db) 
                    for student, grade in results]
            
        finally:
            db.close()
    
    @staticmethod
    def get_cohort_statistics(semester: str, cohort_type: str = 'inperson') -> Dict:
        """
        Get statistical summary for a cohort.
        
        Args:
            semester: Semester code (e.g., '202580')
            cohort_type: 'inperson' or 'online'
            
        Returns:
            Dictionary with statistics:
            - total_students: Count of students
            - avg_lab: Average lab grade
            - avg_quizzes: Average quiz grade
            - avg_exit_tickets: Average exit ticket grade
            - avg_overall_pre: Average pre-final grade
            - avg_overall_post: Average post-final grade
            - students_with_dca: Count of students who submitted DCA
            - passing_rate_pre: Percentage passing before DCA
            - passing_rate_post: Percentage passing after DCA
            
        Example:
            >>> stats = CohortQueries.get_cohort_statistics('202580', 'inperson')
            >>> print(f"Average pre-final grade: {stats['avg_overall_pre']:.2f}%")
            >>> print(f"Passing rate: {stats['passing_rate_pre']:.1f}%")
        """
        if cohort_type.lower() == 'inperson':
            students = CohortQueries.get_inperson_students(semester)
        else:
            students = CohortQueries.get_online_students(semester)
        
        if not students:
            return {
                'total_students': 0,
                'avg_lab': 0.0,
                'avg_quizzes': 0.0,
                'avg_exit_tickets': 0.0,
                'avg_overall_pre': 0.0,
                'avg_overall_post': 0.0,
                'students_with_dca': 0,
                'passing_rate_pre': 0.0,
                'passing_rate_post': 0.0,
            }
        
        total = len(students)
        
        # Calculate averages
        avg_lab = sum(s['lab_average'] for s in students) / total
        avg_quizzes = sum(s['quizzes_average'] for s in students) / total
        avg_exit_tickets = sum(s['exit_tickets_average'] for s in students) / total
        avg_overall_pre = sum(s['overall_pre_final'] for s in students) / total
        avg_overall_post = sum(s['overall_post_final'] for s in students) / total
        
        # Count students with DCA
        students_with_dca = sum(1 for s in students if s['has_final_project'])
        
        # Calculate passing rates (60% threshold)
        passing_pre = sum(1 for s in students if s['overall_pre_final'] >= 60.0)
        passing_post = sum(1 for s in students if s['overall_post_final'] >= 60.0)
        
        # Calculate grade distribution (post-final)
        grade_distribution = {
            'A': sum(1 for s in students if s['overall_post_final'] >= 90.0),
            'B': sum(1 for s in students if 80.0 <= s['overall_post_final'] < 90.0),
            'C': sum(1 for s in students if 70.0 <= s['overall_post_final'] < 80.0),
            'D': sum(1 for s in students if 60.0 <= s['overall_post_final'] < 70.0),
            'F': sum(1 for s in students if s['overall_post_final'] < 60.0),
        }

        # Calculate average DCA score
        students_with_dca_list = [s for s in students if s['has_final_project']]
        avg_dca = sum(s['dca_score'] for s in students_with_dca_list) / len(students_with_dca_list) if students_with_dca_list else 0.0

        return {
            'total_students': total,
            'avg_lab': avg_lab,
            'avg_quizzes': avg_quizzes,
            'avg_exit_tickets': avg_exit_tickets,
            'avg_dca': avg_dca,
            'avg_overall_pre': avg_overall_pre,
            'avg_overall_post': avg_overall_post,
            'students_with_dca': students_with_dca,
            'students_with_lab': sum(1 for s in students if s['lab_average'] > 0),
            'students_with_quizzes': sum(1 for s in students if s['quizzes_average'] > 0),
            'students_with_exit_tickets': sum(1 for s in students if s['exit_tickets_average'] > 0),
            'passing_rate_pre': (passing_pre / total) * 100,
            'passing_rate_post': (passing_post / total) * 100,
            'grade_distribution': grade_distribution,
        }
    
    @staticmethod
    def get_all_students(semester: str) -> List[Dict]:
        """
        Get all students regardless of cohort.
        
        Args:
            semester: Semester code (e.g., '202580')
            
        Returns:
            List of dictionaries containing student info and all grade components
        """
        inperson = CohortQueries.get_inperson_students(semester)
        online = CohortQueries.get_online_students(semester)
        
        # Combine and sort by last name, first name
        all_students = inperson + online
        all_students.sort(key=lambda s: (s['last_name'], s['first_name']))
        
        return all_students
    
    @staticmethod
    def _format_student_grade(student: Student, grade: StudentGrade, db: Session) -> Dict:
        """
        Format student and grade information into a dictionary with section info.
        
        Returns a dictionary with all student info, grade components,
        and the actual section names for both lab and lecture.
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
