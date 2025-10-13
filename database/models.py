from sqlalchemy import (
    Column, String, Float, DateTime, ForeignKey,
    CheckConstraint, Index, UniqueConstraint
)
from sqlalchemy.orm import relationship
from datetime import datetime
from .connection import Base
import uuid

def get_current_semester():
    now = datetime.now()
    if now.month < 5: semester = '10'
    elif (now.month > 7 and now.day > 15): semester = '80'
    else: semester = '50'
    return f"{now.year}{semester}"

class Student(Base):
    __tablename__ = 'students'
    org_defined_id = Column(String(20), primary_key=True)
    username = Column(String(100), nullable=False, index=True)
    email = Column(String(255), nullable=False, index=True)
    last_name = Column(String(100), nullable=False)
    first_name = Column(String(100), nullable=False)
    
    # Relationships
    grade_snapshots = relationship('GradeSnapshot', back_populates='student', cascade='all, delete-orphan')
    grades = relationship('StudentGrade', back_populates='student', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<Student {self.first_name} {self.last_name} ({self.org_defined_id})>"


class Course(Base):
    __tablename__ = 'courses'
    
    ou = Column(String(20), primary_key=True)
    course_name = Column(String(200), nullable=False)
    course_type = Column(String(10), nullable=False)  # 'LAB' or 'LECTURE'
    section = Column(String(50))
    semester = Column(String(50), index=True)
    
    # Relationships
    grade_snapshots = relationship('GradeSnapshot', back_populates='course')
    lab_grades = relationship('StudentGrade', foreign_keys='StudentGrade.lab_course_ou', back_populates='lab_course')
    lecture_grades = relationship('StudentGrade', foreign_keys='StudentGrade.lecture_course_ou', back_populates='lecture_course')
    
    __table_args__ = (
        CheckConstraint("course_type IN ('LAB', 'LECTURE')", name='check_course_type'),
        Index('idx_course_name_type', 'course_name', 'course_type'),
    )

    def __repr__(self):
        return f"<Course {self.course_name} - {self.course_type} ({self.semester})>"


class GradeSnapshot(Base):
    __tablename__ = 'grade_snapshots'
    
    id = Column(String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    student_id = Column(String(20), ForeignKey('students.org_defined_id'), nullable=False)
    course_ou = Column(String(20), ForeignKey('courses.ou'), nullable=False)
    snapshot_date = Column(DateTime, nullable=False, default=datetime.now, index=True)

    # Lab-specific fields
    lab_numerator = Column(Float)
    lab_denominator = Column(Float)
    lab_average = Column(Float)
    dca_score = Column(Float, default=0)
    
    # Lecture-specific fields
    quizzes_numerator = Column(Float)
    quizzes_denominator = Column(Float)
    quizzes_average = Column(Float)
    exit_tickets_numerator = Column(Float)
    exit_tickets_denominator = Column(Float)
    exit_tickets_average = Column(Float)
    
    # Relationships
    student = relationship('Student', back_populates='grade_snapshots')
    course = relationship('Course', back_populates='grade_snapshots')

    __table_args__ = (
        Index('idx_student_course_date', 'student_id', 'course_ou', 'snapshot_date'),
        CheckConstraint('lab_average >= 0 AND lab_average <= 100', name='check_lab_average_range'),
        CheckConstraint('dca_score >= 0 AND dca_score <= 100', name='check_dca_score_range'),
        CheckConstraint('quizzes_average >= 0 AND quizzes_average <= 100', name='check_quizzes_average_range'),
        CheckConstraint('exit_tickets_average >= 0 AND exit_tickets_average <= 100', name='check_exit_tickets_average_range'),
    )
    
    def __repr__(self):
        return f"<GradeSnapshot {self.student_id} - {self.course_ou} @ {self.snapshot_date}>"


class StudentGrade(Base):
    __tablename__ = 'student_grades'
    
    id = Column(String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    student_id = Column(String(20), ForeignKey('students.org_defined_id'), nullable=False)
    semester = Column(String(50), nullable=False, index=True)

    # Lab course and grades
    lab_course_ou = Column(String(20), ForeignKey('courses.ou'))
    lab_numerator = Column(Float)
    lab_denominator = Column(Float)
    lab_average = Column(Float)
    dca_score = Column(Float, default=0)
    
    # Lecture course and grades
    lecture_course_ou = Column(String(20), ForeignKey('courses.ou'))
    quizzes_numerator = Column(Float)
    quizzes_denominator = Column(Float)
    quizzes_average = Column(Float)
    exit_tickets_numerator = Column(Float)
    exit_tickets_denominator = Column(Float)
    exit_tickets_average = Column(Float)
    
    # Calculated fields
    overall_grade_pre_final = Column(Float)
    overall_grade_post_final = Column(Float)
    
    last_updated = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relationships
    student = relationship('Student', back_populates='grades')
    lab_course = relationship('Course', foreign_keys=[lab_course_ou], back_populates='lab_grades')
    lecture_course = relationship('Course', foreign_keys=[lecture_course_ou], back_populates='lecture_grades')
    
    __table_args__ = (
        UniqueConstraint('student_id', 'semester', name='uq_student_semester'),
        Index('idx_student_semester', 'student_id', 'semester'),
        Index('idx_overall_pre_final', 'overall_grade_pre_final'),
        Index('idx_overall_post_final', 'overall_grade_post_final'),
    )

    def calculate_overall_grades(self):
        """
        Calculate and update overall grades based on current component scores.
        Returns tuple: (pre_final_grade, post_final_grade)
        """
        components = []
        if self.lab_average is not None:
            components.append(self.lab_average)
        if self.quizzes_average is not None:
            components.append(self.quizzes_average)
        if self.exit_tickets_average is not None:
            components.append(self.exit_tickets_average)
        
        # Calculate pre-final grade
        if len(components) > 0:
            self.overall_grade_pre_final = sum(components) / 3
        else:
            self.overall_grade_pre_final = None
        
        # Calculate post-final grade (only if dca_score > 0)
        if self.overall_grade_pre_final is not None and self.dca_score and self.dca_score > 0:
            self.overall_grade_post_final = (self.overall_grade_pre_final + self.dca_score) / 2
        else:
            self.overall_grade_post_final = None
        
        return self.overall_grade_pre_final, self.overall_grade_post_final
    
    @property
    def current_grade(self):
        """Returns the appropriate grade: post-final if available, otherwise pre-final"""
        if self.overall_grade_post_final is not None:
            return self.overall_grade_post_final
        return self.overall_grade_pre_final
    
    @property
    def has_final_project(self):
        """Check if final project has been submitted (dca_score > 0)"""
        return self.dca_score is not None and self.dca_score > 0
    
    def __repr__(self):
        grade_str = f"{self.current_grade:.2f}%" if self.current_grade else "N/A"
        return f"<StudentGrade {self.student_id} - {self.semester} - {grade_str}>"
