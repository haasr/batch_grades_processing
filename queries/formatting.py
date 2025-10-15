"""
Formatting utilities for displaying query results.

This module provides functions to format query results into readable text
for display in GUI text areas or console output.
"""

from typing import List, Dict, Optional
from datetime import datetime


class GradeFormatter:
    """Utilities for formatting grade data into readable text."""
    
    @staticmethod
    def format_single_student(student: Dict) -> str:
        """
        Format a single student's complete grade profile.
        
        Args:
            student: Dictionary containing student info and grades
            
        Returns:
            Formatted multi-line string suitable for display
        """
        if not student:
            return "Student not found."
        
        lines = []
        lines.append("=" * 80)
        lines.append("STUDENT INFORMATION")
        lines.append("=" * 80)
        lines.append(f"Name:              {student['first_name']} {student['last_name']}")
        lines.append(f"Username:          {student['username']}")
        lines.append(f"Email:             {student['email']}")
        lines.append(f"Org Defined ID:    {student['org_defined_id']}")
        
        if student['lab_section'] or student['lecture_section']:
            lines.append("")
            lines.append("-" * 80)
            lines.append("ENROLLMENT")
            lines.append("-" * 80)
            if student['lab_section']:
                lines.append(f"Lab Section:       {student['lab_section']}")
            if student['lecture_section']:
                lines.append(f"Lecture Section:   {student['lecture_section']}")
        
        # Only show grades if they exist
        if student['semester']:
            lines.append("")
            lines.append("-" * 80)
            lines.append(f"GRADES - SEMESTER {student['semester']}")
            lines.append("-" * 80)
            
            # Lab grades
            lines.append("")
            lines.append("Lab Assignments:")
            lines.append(f"  Score:           {student['lab_numerator']:.2f} / {student['lab_denominator']:.2f}")
            lines.append(f"  Average:         {student['lab_average']:.2f}%")
            
            # DCA
            lines.append("")
            lines.append("Digital Citizenship Audit (Final Project):")
            if student['has_final_project']:
                lines.append(f"  Score:           {student['dca_score']:.2f}%")
            else:
                lines.append(f"  Score:           Not yet graded")
            
            # Lecture grades
            lines.append("")
            lines.append("Quizzes:")
            lines.append(f"  Score:           {student['quizzes_numerator']:.2f} / {student['quizzes_denominator']:.2f}")
            lines.append(f"  Average:         {student['quizzes_average']:.2f}%")
            
            lines.append("")
            lines.append("Exit Tickets:")
            lines.append(f"  Score:           {student['exit_tickets_numerator']:.2f} / {student['exit_tickets_denominator']:.2f}")
            lines.append(f"  Average:         {student['exit_tickets_average']:.2f}%")
            
            # Overall grades
            lines.append("")
            lines.append("=" * 80)
            lines.append("OVERALL GRADES")
            lines.append("=" * 80)
            lines.append(f"Pre-Final Grade:   {student['overall_pre_final']:.2f}%")
            lines.append(f"Post-Final Grade:  {student['overall_post_final']:.2f}%")
            
            if not student['has_final_project']:
                lines.append("")
                lines.append("⚠️  WARNING: Post-final grade shows 50% penalty for missing DCA")
            
            if student['last_updated']:
                lines.append("")
                lines.append(f"Last Updated: {student['last_updated'].strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            lines.append("")
            lines.append("No grade records found for this semester.")
        
        lines.append("=" * 80)
        
        return "\n".join(lines)
    
    @staticmethod
    def format_student_list(students: List[Dict], show_full_grades: bool = False) -> str:
        """
        Format a list of students in a table format.
        
        Args:
            students: List of student dictionaries
            show_full_grades: If True, show all grade components. If False, show summary only.
            
        Returns:
            Formatted multi-line string suitable for display
        """
        if not students:
            return "No students found."
        
        lines = []
        lines.append(f"Found {len(students)} student(s)")
        lines.append("")
        
        if show_full_grades:
            # Full format with all grade components
            lines.append("=" * 160)
            header = (
                f"{'Name':<25} {'Username':<15} {'Lab':<8} {'Quiz':<8} {'ExTix':<8} "
                f"{'DCA':<8} {'Pre':<8} {'Post':<8} {'Sections':<36}"
            )
            lines.append(header)
            lines.append("=" * 160)
            
            for student in students:
                name = f"{student['last_name']}, {student['first_name']}"[:24]
                username = student['username'][:14]
                lab = f"{student['lab_average']:.2f}%"
                quiz = f"{student['quizzes_average']:.2f}%"
                extix = f"{student['exit_tickets_average']:.2f}%"
                
                if student['has_final_project']:
                    dca = f"{student['dca_score']:.2f}%"
                else:
                    dca = "N/A"
                
                pre = f"{student['overall_pre_final']:.2f}%"
                post = f"{student['overall_post_final']:.2f}%"
                
                sections = f"Lab:{student['lab_section'] or 'N/A'} Lec:{student['lecture_section'] or 'N/A'}"[:36]
                
                line = (
                    f"{name:<25} {username:<15} {lab:<8} {quiz:<8} {extix:<8} "
                    f"{dca:<8} {pre:<8} {post:<8} {sections:<30}"
                )
                lines.append(line)
        else:
            # Summary format
            lines.append("=" * 120)
            header = (
                f"{'Name':<30} {'Username':<15} {'OrgID':<12} "
                f"{'Pre-Final':<10} {'Post-Final':<10} {'Sections':<36}"
            )
            lines.append(header)
            lines.append("=" * 120)
            
            for student in students:
                name = f"{student['last_name']}, {student['first_name']}"[:29]
                username = student['username'][:14]
                org_id = student['org_defined_id'][:11]
                pre = f"{student['overall_pre_final']:.2f}%"
                post = f"{student['overall_post_final']:.2f}%"
                
                lab_sec = student['lab_section'] or 'N/A'
                lec_sec = student['lecture_section'] or 'N/A'
                sections = f"Lab:{lab_sec} Lec:{lec_sec}"[:35]
                
                line = (
                    f"{name:<30} {username:<15} {org_id:<12} "
                    f"{pre:<10} {post:<10} {sections:<35}"
                )
                lines.append(line)
        
        lines.append("=" * (160 if show_full_grades else 120))
        
        return "\n".join(lines)
    
    @staticmethod
    def format_cohort_statistics(stats: Dict, cohort_type: str) -> str:
        """
        Format cohort statistics in a readable format.
        
        Args:
            stats: Dictionary with statistical data
            cohort_type: 'inperson' or 'online'
            
        Returns:
            Formatted multi-line string suitable for display
        """
        cohort_name = "IN-PERSON" if cohort_type.lower() == 'inperson' else "ONLINE"
        
        lines = []
        lines.append("=" * 80)
        lines.append(f"{cohort_name} COHORT STATISTICS")
        lines.append("=" * 80)
        lines.append("")
        lines.append(f"Total Students:              {stats['total_students']}")
        lines.append(f"Students with DCA:           {stats['students_with_dca']} "
                    f"({stats['students_with_dca']/stats['total_students']*100:.1f}%)")
        lines.append("")
        lines.append("-" * 80)
        lines.append("AVERAGE GRADES")
        lines.append("-" * 80)
        lines.append(f"Lab Assignments:             {stats['avg_lab']:.2f}%")
        lines.append(f"Quizzes:                     {stats['avg_quizzes']:.2f}%")
        lines.append(f"Exit Tickets:                {stats['avg_exit_tickets']:.2f}%")
        lines.append("")
        lines.append(f"Overall Pre-Final:           {stats['avg_overall_pre']:.2f}%")
        lines.append(f"Overall Post-Final:          {stats['avg_overall_post']:.2f}%")
        lines.append("")
        lines.append("-" * 80)
        lines.append("PASSING RATES (60% threshold)")
        lines.append("-" * 80)
        lines.append(f"Pre-Final Passing Rate:      {stats['passing_rate_pre']:.1f}%")
        lines.append(f"Post-Final Passing Rate:     {stats['passing_rate_post']:.1f}%")
        lines.append("=" * 80)
        
        return "\n".join(lines)
    
    @staticmethod
    def format_section_summary(students: List[Dict], section_name: str) -> str:
        """
        Format a section summary with student list and statistics.
        
        Args:
            students: List of student dictionaries
            section_name: Name of the section (e.g., 'CSCI-1150-001')
            
        Returns:
            Formatted multi-line string suitable for display
        """
        if not students:
            return f"No students found in section {section_name}"
        
        lines = []
        lines.append("=" * 80)
        lines.append(f"SECTION: {section_name}")
        lines.append("=" * 80)
        lines.append(f"Total Students: {len(students)}")
        lines.append("")
        
        # Calculate section statistics
        avg_pre = sum(s['overall_pre_final'] for s in students) / len(students)
        avg_post = sum(s['overall_post_final'] for s in students) / len(students)
        students_with_dca = sum(1 for s in students if s['has_final_project'])
        passing_pre = sum(1 for s in students if s['overall_pre_final'] >= 60.0)
        passing_post = sum(1 for s in students if s['overall_post_final'] >= 60.0)
        
        lines.append("SECTION STATISTICS:")
        lines.append(f"  Average Pre-Final:       {avg_pre:.2f}%")
        lines.append(f"  Average Post-Final:      {avg_post:.2f}%")
        lines.append(f"  Students with DCA:       {students_with_dca}/{len(students)}")
        lines.append(f"  Passing Rate (Pre):      {passing_pre}/{len(students)} ({passing_pre/len(students)*100:.1f}%)")
        lines.append(f"  Passing Rate (Post):     {passing_post}/{len(students)} ({passing_post/len(students)*100:.1f}%)")
        lines.append("")
        lines.append("=" * 80)
        lines.append("")
        
        # Add student list
        lines.append(GradeFormatter.format_student_list(students, show_full_grades=False))
        
        return "\n".join(lines)
