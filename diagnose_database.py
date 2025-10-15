"""
Database diagnostic script - check what's actually stored.

This script helps debug issues with grade data not being saved properly.
"""

from database import get_db, Student, Course, StudentGrade, GradeSnapshot

def check_database_contents(semester='202580'):
    """Check what's actually in the database."""
    db = get_db()

    try:
        print("\n" + "="*80)
        print("DATABASE DIAGNOSTIC REPORT")
        print("="*80)

        # Check Students
        students = db.query(Student).all()
        print(f"\n📊 Students: {len(students)} total")
        if students:
            print("\nSample students:")
            for s in students[:3]:
                print(f"  - {s.first_name} {s.last_name} ({s.username}) - {s.org_defined_id}")

        # Check Courses
        courses = db.query(Course).filter_by(semester=semester).all()
        print(f"\n📚 Courses for {semester}: {len(courses)} total")
        lab_courses = [c for c in courses if c.course_type == 'LAB']
        lecture_courses = [c for c in courses if c.course_type == 'LECTURE']
        print(f"  - Lab courses: {len(lab_courses)}")
        print(f"  - Lecture courses: {len(lecture_courses)}")

        if courses:
            print("\nSample courses:")
            for c in courses[:5]:
                print(f"  - {c.course_name}-{c.section} ({c.course_type}) - OU: {c.ou}")

        # Check StudentGrades
        grades = db.query(StudentGrade).filter_by(semester=semester).all()
        print(f"\n📝 StudentGrade records for {semester}: {len(grades)} total")

        if grades:
            # Check how many have data
            with_lab = sum(1 for g in grades if g.lab_average and g.lab_average > 0)
            with_lecture = sum(1 for g in grades if g.quizzes_average and g.quizzes_average > 0)
            with_dca = sum(1 for g in grades if g.dca_score and g.dca_score > 0)
            with_overall_pre = sum(1 for g in grades if g.overall_grade_pre_final and g.overall_grade_pre_final > 0)
            with_overall_post = sum(1 for g in grades if g.overall_grade_post_final and g.overall_grade_post_final > 0)
            
            print(f"  - With lab data: {with_lab}")
            print(f"  - With lecture data: {with_lecture}")
            print(f"  - With DCA scores: {with_dca}")
            print(f"  - With pre-final grade: {with_overall_pre}")
            print(f"  - With post-final grade: {with_overall_post}")
            
            # Show sample records
            print("\n🔍 Sample StudentGrade records:")
            for g in grades[:3]:
                print(f"\n  Student: {g.student_id}")
                print(f"    Semester: {g.semester}")
                print(f"    Lab Course OU: {g.lab_course_ou}")
                print(f"    Lab Average: {g.lab_average}")
                print(f"    DCA Score: {g.dca_score}")
                print(f"    Lecture Course OU: {g.lecture_course_ou}")
                print(f"    Quizzes Average: {g.quizzes_average}")
                print(f"    Exit Tickets Average: {g.exit_tickets_average}")
                print(f"    Overall Pre-Final: {g.overall_grade_pre_final}")
                print(f"    Overall Post-Final: {g.overall_grade_post_final}")

        # Check GradeSnapshots
        snapshots = db.query(GradeSnapshot).all()
        print(f"\n📸 GradeSnapshot records: {len(snapshots)} total")
        if snapshots:
            lab_snapshots = sum(1 for s in snapshots if s.lab_average is not None)
            lecture_snapshots = sum(1 for s in snapshots if s.quizzes_average is not None)
            print(f"  - With lab data: {lab_snapshots}")
            print(f"  - With lecture data: {lecture_snapshots}")

        # Identify problems
        print("\n" + "="*80)
        print("POTENTIAL ISSUES")
        print("="*80)

        issues_found = False

        if len(grades) == 0:
            print("\n❌ PROBLEM: No StudentGrade records found!")
            print("   This means save_grades_to_db() isn't creating/updating records.")
            issues_found = True
        elif with_lab == 0 and with_lecture == 0:
            print("\n❌ PROBLEM: StudentGrade records exist but have NO grade data!")
            print("   This means the fields aren't being set properly.")
            issues_found = True
        elif with_overall_pre == 0:
            print("\n❌ PROBLEM: No overall_grade_pre_final calculated!")
            print("   This means calculate_overall_grades() isn't working or isn't being called.")
            issues_found = True

        # Check for records with semester=None
        bad_semesters = db.query(StudentGrade).filter(
            (StudentGrade.semester == None) | (StudentGrade.semester == '')
        ).all()
        if bad_semesters:
            print(f"\n⚠️  WARNING: {len(bad_semesters)} StudentGrade records with semester=None")
            print("   These records exist but can't be queried properly.")
            issues_found = True

        # Check for orphaned records (student exists but no grades)
        students_with_grades = set(g.student_id for g in grades)
        students_without_grades = [s for s in students if s.org_defined_id not in students_with_grades]
        if students_without_grades:
            print(f"\n⚠️  INFO: {len(students_without_grades)} students have no StudentGrade records")
            print("   This is normal if they're from different semesters.")

        if not issues_found:
            print("\n✅ No obvious problems detected!")
            print("   Data appears to be saved correctly.")

        print("\n" + "="*80)

    finally:
        db.close()


def check_specific_student(username=None, org_id=None, semester='202580'):
    """Deep dive into a specific student's data."""
    db = get_db()

    try:
        print("\n" + "="*80)
        print("STUDENT DEEP DIVE")
        print("="*80)

        # Find student
        if username:
            student = db.query(Student).filter_by(username=username).first()
        elif org_id:
            student = db.query(Student).filter_by(org_defined_id=org_id).first()
        else:
            print("❌ Must provide username or org_id")
            return

        if not student:
            print(f"❌ Student not found")
            return

        print(f"\n👤 Student: {student.first_name} {student.last_name}")
        print(f"   Username: {student.username}")
        print(f"   Email: {student.email}")
        print(f"   Org ID: {student.org_defined_id}")

        # Check StudentGrade
        grade = db.query(StudentGrade).filter_by(
            student_id=student.org_defined_id,
            semester=semester
        ).first()

        if not grade:
            print(f"\n❌ No StudentGrade record found for semester {semester}")
            
            # Check if record exists with different/null semester
            all_grades = db.query(StudentGrade).filter_by(
                student_id=student.org_defined_id
            ).all()
            if all_grades:
                print(f"\n⚠️  Found {len(all_grades)} StudentGrade records with other semesters:")
                for g in all_grades:
                    print(f"   - Semester: {g.semester}")
            return

        print(f"\n📝 StudentGrade Record:")
        print(f"   Semester: {grade.semester}")
        print(f"   Lab Course OU: {grade.lab_course_ou}")
        print(f"   Lab Numerator: {grade.lab_numerator}")
        print(f"   Lab Denominator: {grade.lab_denominator}")
        print(f"   Lab Average: {grade.lab_average}")
        print(f"   DCA Score: {grade.dca_score}")
        print(f"   Lecture Course OU: {grade.lecture_course_ou}")
        print(f"   Quizzes Numerator: {grade.quizzes_numerator}")
        print(f"   Quizzes Denominator: {grade.quizzes_denominator}")
        print(f"   Quizzes Average: {grade.quizzes_average}")
        print(f"   Exit Tickets Numerator: {grade.exit_tickets_numerator}")
        print(f"   Exit Tickets Denominator: {grade.exit_tickets_denominator}")
        print(f"   Exit Tickets Average: {grade.exit_tickets_average}")
        print(f"   Overall Pre-Final: {grade.overall_grade_pre_final}")
        print(f"   Overall Post-Final: {grade.overall_grade_post_final}")
        print(f"   Has Final Project: {grade.has_final_project}")
        print(f"   Last Updated: {grade.last_updated}")

        # Check snapshots
        snapshots = db.query(GradeSnapshot).filter_by(
            student_id=student.org_defined_id
        ).order_by(GradeSnapshot.snapshot_date.desc()).all()

        print(f"\n📸 Grade Snapshots: {len(snapshots)}")
        if snapshots:
            print("\n   Most recent snapshots:")
            for s in snapshots[:3]:
                print(f"   - {s.snapshot_date}: Course OU {s.course_ou}")
                if s.lab_average:
                    print(f"     Lab: {s.lab_average:.2f}%")
                if s.quizzes_average:
                    print(f"     Quizzes: {s.quizzes_average:.2f}%")

        print("\n" + "="*80)

    finally:
        db.close()


if __name__ == '__main__':
    import sys
    
    # Check overall database
    check_database_contents()

    # If username provided, check specific student
    if len(sys.argv) > 1:
        username = sys.argv[1]
        print("\n")
        check_specific_student(username=username)

    print("\n💡 To check a specific student:")
    print("   python diagnose_database.py <username>")
