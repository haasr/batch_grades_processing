from .d2l_grades_scraper import D2LGradesScraper
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from typing import List
from pathlib import Path
from database.models import *
from database import get_db
from dotenv import load_dotenv
import traceback
import pandas as pd
import time
import os


pd.options.mode.chained_assignment = None  # Suppresses warnings
# Initialize constants
CURRENT_SEMESTER = get_current_semester()
CURRENT_DIR = Path(os.path.dirname(os.path.abspath(__file__)))
# Load environment variables
load_dotenv((CURRENT_DIR / '.env').as_posix())


class LabGradesScraper(D2LGradesScraper):
    def __init__(self, ous_list: List[str], headless=False, webdriver_path=None):
        downloads_dir = CURRENT_DIR / 'downloads'
        os.makedirs(downloads_dir, exist_ok=True)
        downloads_dir = downloads_dir / 'lab_grades'
        super().__init__(ous_list=ous_list, downloads_dir=downloads_dir,
                         headless=headless, webdriver_path=webdriver_path)

        # Get score info from env vars
        self.modify_grade_calc_options = bool(int(os.getenv('MODIFY_GRADE_CALC_OPTIONS', 0)))
        self.drop_ungraded_items = bool(int(os.getenv('DROP_UNGRADED_ITEMS', 0)))
        # Label for lab assignments category and final project assignment (in gradebook)
        self.lab_assignments_category_label = os.getenv('LAB_ASSIGNMENTS_CATEGORY_LABEL', 'Lab')
        self.final_project_label = os.getenv('FINAL_PROJECT_LABEL', 'Audit')
        # Wipe grades files before quitting
        self.delete_downloads_on_completion = bool(int(os.getenv('DELETE_DOWNLOADS_ON_COMPLETION', 1)))

        self.worker_id = os.getpid()
        self.logger = self.setup_worker_logger()

        self.logger.info(f"[{self.__class__.__name__}] Downloads dir = {self.downloads_dir}")

    def export_users_grades(self, ou: str) -> bool:
        """
        Navigate to the grade export page and configure the export options.
        """
        try:
            # Navigate to the export grades page
            self.driver.get(f"https://elearn.etsu.edu/d2l/lms/grades/admin/importexport/export/options_edit.d2l?ou={ou}")
            wait = WebDriverWait(self.driver, 10)

            # 1. Ensure the Key Field is set to Org Defined ID
            self._set_key_field_to_org_id()
            # 2. Ensure Points grade Grade Values option (exclusively) is checked
            self._set_grade_values_to_points_grade()
            # 3. Select all user details, including Section Membership
            self._select_all_user_details()
            
            # First find the specific table
            grade_table = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "table.d2l-table.d2l-grid.d_gl"))
            )
            
            # Get all rows except the header row
            grade_rows = grade_table.find_elements(By.TAG_NAME, "tr")[1:]  # Skip header row
            
            ### Find and select ONLY the final project (all else deselected)
            final_project_label = self.final_project_label.lower()
            for row in grade_rows:
                try:
                    # Get the label text and checkbox for this row
                    label_elem = row.find_element(By.CSS_SELECTOR, "th.d_ich label")
                    label_text = label_elem.text
                    label_text = label_text.lower()
                    
                    checkbox = row.find_element(By.CSS_SELECTOR, "input[type='checkbox']")
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", row)
                    time.sleep(0.2)  # Brief pause to let the scroll complete
                    if label_text.startswith(final_project_label):
                        if not checkbox.is_selected(): checkbox.click()
                        self.logger.info(f"[{self.__class__.__name__}] Selected grade item: {label_text}")
                    else:
                        if checkbox.is_selected(): checkbox.click()
                except Exception as e:
                    self.logger.error(f"[{self.__class__.__name__}] Error processing row: {str(e)}")
                    continue
            
            # NOTE: This block must come AFTER the above for loop bc it deselects all but the final project
            # Crash the program if this fails -- we have to have the labs subtotal:
            try:
                # There are at least two with the same aria label because of fucking D2L...
                # The first is the Lab assignments category label, so the last one
                # should be the subtotal
                lab_subtotal_checkboxes = grade_table.find_elements(
                    By.CSS_SELECTOR,
                    f'input.d2l-checkbox[aria-label="Select {self.lab_assignments_category_label}"]'
                )
                lab_subtotal_checkbox = lab_subtotal_checkboxes[-1] # This one is the subtotal

                self.driver.execute_script("arguments[0].scrollIntoView(true);", lab_subtotal_checkbox)
                time.sleep(0.3)
                if not lab_subtotal_checkbox.is_selected(): lab_subtotal_checkbox.click()
            except Exception as e:
                self.logger.error(f"[{self.__class__.__name__}]\nFATAL: Could not select the Labs subtotal!\n{str(e)}")
                print("Exiting...")
                self.close()
                exit(1)

            # Now handle the export button
            # First scroll back to top to ensure floating buttons are visible
            self.driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(0.5)
            
            # Find and click the Export to CSV button within d2l-floating-buttons
            export_button = wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "d2l-floating-buttons button.d2l-button"))
            )
            export_button.click()
            ##################################################################
            # After clicking export, wait for the popup
            wait.until(
                EC.presence_of_element_located((By.CLASS_NAME, "ddial_o"))
            )
            
            self.logger.info(f"[{self.__class__.__name__}] Export window opened, waiting for processing...")

            # Wait a bit to ensure the download button is ready
            time.sleep(12)
            
            # Find and click the Download button within the dialog
            download_button = wait.until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, "table.d2l-dialog-buttons button.d2l-button[primary]")
                )
            )
            download_button.click()
            time.sleep(2)

            return True
            
        except Exception as e:
            self.logger.error(f"[{self.__class__.__name__}] Failed to configure export options: {str(e)}")
            self.logger.debug(traceback.format_exc())
            return False
    
    def parse_data_from_grades_csv(self, course_name: str, ou: str):
        file_path = self.get_csv_by_course_name(course_name)
        self.logger.debug(f"[{self.__class__.__name__}] Latest file CSV file is {file_path}")
        if not file_path:
            self.logger.error(f"[{self.__class__.__name__}] CSV file not found in {self.downloads_dir}")
            return False

        try:
            df = pd.read_csv(file_path)
            df.drop('End-of-Line Indicator', axis=1, inplace=True) # Stupid
            df['OrgDefinedId'] = df['OrgDefinedId'].str.replace('#', '') # Also stupid
            df['OrgDefinedId'] = df['OrgDefinedId'].astype(str)
            df['Email'] = df['Email'].apply(lambda x: x.lower())
            df['Username'] = df['Email'].apply(lambda x: x.split('@')[0])
            # Reorder -- Put username directly right Email:
            other_cols = df.columns[:-1].tolist()
            new_column_order = other_cols[:4] + ['Username'] + other_cols[4:]
            df = df[new_column_order]

            labs_subtotal_numerator_idx = -1
            labs_subtotal_denominator_idx = -1
            final_project_idx = -1
            final_project_maxpoints = 100
            last_name_idx = -1
            first_name_idx = -1

            cols = list(df.columns)

            for i, col in enumerate(cols):
                colname = col.lower()
                if "numerator" in colname:
                    labs_subtotal_numerator_idx = i
                elif "denominator" in colname:
                    labs_subtotal_denominator_idx = i
                elif "last" in colname: # don't check for "name" since it is in username
                    first_name_idx = i
                elif "first" in colname:
                    last_name_idx = i
                elif colname.strip().startswith(self.final_project_label.lower()):
                    final_project_idx = i
                    # Find out the max points to correctly calculate the score (out of 100 or 300?, etc.)
                    if 'maxpoints:' in colname:
                        numeric_s = ""
                        points_split = col.split(':')[1]
                        for c in points_split:
                            if c.isdigit(): numeric_s += c
                        # Don't use try/except so this will crash if there's a problem
                        final_project_maxpoints = int(numeric_s)

            df = df.rename(columns={
                cols[last_name_idx]: "Last_Name",
                cols[first_name_idx]: "First_Name",
                cols[labs_subtotal_numerator_idx]: "lab_numerator",
                cols[labs_subtotal_denominator_idx]: "lab_denominator",
                cols[final_project_idx]: "dca_score"
            })

            # Fill nans with 0. DO NOT DROP nan data!!
            df['lab_numerator'] = df['lab_numerator'].fillna(0)
            df['lab_denominator'] = df['lab_denominator'].fillna(0)
            df['dca_score'] = df['dca_score'].fillna(0)
            
            # Normalize DCA score to percentage (works fine when scores aren't in yet)
            df['dca_score'] = df['dca_score'].apply(lambda x: 100*(x/final_project_maxpoints))

            # Ensure numeric
            df = df.astype({'lab_numerator': float, 'lab_denominator': float, 'dca_score': float})
            # Replace any 0s in denominator column with mode (avert possibility of divide by zero)
            mode_series = df['lab_denominator'].mode()
            denom_mode = float(mode_series[0])
            df['lab_denominator'] = df['lab_denominator'].replace(0, denom_mode)
            
            # Calculate new column: lab average (keep unrounded percentage)
            df['lab_average'] = (
                100 * (df['lab_numerator'] / df['lab_denominator'])
            )
            # Append to list of all the lab sections' grades
            self.grades_dataframes_map[f"{course_name}_{ou}"] = df
            return True
        except Exception as e:
            self.logger.error(f"[{self.__class__.__name__}] Error parsing grade file data: {str(e)}")
            self.logger.debug(traceback.format_exc())
            return False

    def save_grades_to_db(self, semester: str = None):
        """Save lab grades to database after scraping."""
        db = get_db()

        if not semester:
            semester = CURRENT_SEMESTER

        try:
            for course_ou, df in self.grades_dataframes_map.items():
                self.logger.info(f"Saving {len(df)} lab records for {course_ou}")
                course_split = course_ou.split("_")
                course_name = course_split[0]
                ou = course_split[1]

                course_name_split = course_name.split("-")
                course_name = f"{course_name_split[0]}-{course_name_split[1]}"
                section = course_name_split[2]

                # Get or create course
                course = db.query(Course).filter_by(ou=ou).first()
                if not course:
                    course = Course(
                        ou=ou,
                        course_name=course_name,
                        course_type='LAB',
                        section=section,
                        semester=semester
                    )
                    db.add(course)
                    db.flush()

                for row in df.itertuples(index=False):
                    org_id = str(row.OrgDefinedId)

                    # Get or create student
                    student = db.query(Student).filter_by(org_defined_id=org_id).first()
                    if not student:
                        student = Student(
                            org_defined_id=org_id,
                            username=str(row.Username),
                            email=str(row.Email),
                            last_name=str(row.Last_Name),   # NOTE: Column names with spaces must be written with underscore
                            first_name=str(row.First_Name),
                        )
                        db.add(student)
                        db.flush()

                    # Create snapshot
                    snapshot = GradeSnapshot(
                        student_id=org_id,
                        course_ou=ou,
                        lab_numerator=float(row.lab_numerator) if not pd.isna(row.lab_numerator) else 0.0,
                        lab_denominator=float(row.lab_denominator) if not pd.isna(row.lab_denominator) else 0.0,
                        lab_average=float(row.lab_average) if not pd.isna(row.lab_average) else 0.0,
                        dca_score=float(row.dca_score) if not pd.isna(row.dca_score) else 0.0,
                    )
                    db.add(snapshot)

                    # Update or create StudentGrade
                    student_grade = db.query(StudentGrade).filter_by(
                        student_id=org_id,
                        semester=semester
                    ).first()

                    if not student_grade:
                        student_grade = StudentGrade(
                            student_id=org_id,
                            semester=semester
                        )
                        db.add(student_grade)

                    # Update lab fields
                    student_grade.lab_course_ou = ou
                    student_grade.lab_numerator = float(row.lab_numerator) if not pd.isna(row.lab_numerator) else 0.0
                    student_grade.lab_denominator = float(row.lab_denominator) if not pd.isna(row.lab_denominator) else 0.0
                    student_grade.lab_average = float(row.lab_average) if not pd.isna(row.lab_average) else 0.0
                    student_grade.dca_score = float(row.dca_score) if not pd.isna(row.dca_score) else 0.0

                    # Calculate overall grades
                    student_grade.calculate_overall_grades()

                db.commit()
                self.logger.info(f"Successfully saved {course_name} lab grades")

        except Exception as e:
            db.rollback()
            self.logger.error(f"Error saving to database: {str(e)}")
            raise
        finally:
            db.close()
