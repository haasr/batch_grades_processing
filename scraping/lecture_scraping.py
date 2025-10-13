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


class LectureGradesScraper(D2LGradesScraper):
    def __init__(self, ous_list: List[str], headless=False, webdriver_path=None):
        downloads_dir = CURRENT_DIR / 'downloads'
        os.makedirs(downloads_dir, exist_ok=True)
        downloads_dir = downloads_dir / 'lecture_grades'

        super().__init__(ous_list=ous_list, downloads_dir=downloads_dir,
                         headless=headless, webdriver_path=webdriver_path)

        # Labels for quizzes category and exit tickets category (in gradebook)
        # Get score info from env vars
        self.modify_grade_calc_options = bool(int(os.getenv('MODIFY_GRADE_CALC_OPTIONS', 0)))
        self.drop_ungraded_items = bool(int(os.getenv('DROP_UNGRADED_ITEMS', 0)))
        # Labels for quizzes assignments category and exit texits assignments category (in gradebook)
        self.quizzes_category_label = os.getenv('QUIZZES_CATEGORY_LABEL', 'Quizzes')
        self.exit_tickets_category_label = os.getenv('EXIT_TICKETS_CATEGORY_LABEL', 'Exit Tickets')
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

            ### 1. Deselect all
            for row in grade_rows:
                try:
                    # Get the label text and checkbox for this row
                    label_elem = row.find_element(By.CSS_SELECTOR, "th.d_ich label")
                    label_text = label_elem.text
                    label_text = label_text.lower()

                    checkbox = row.find_element(By.CSS_SELECTOR, "input[type='checkbox']")
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", row)
                    time.sleep(0.2)  # Brief pause to let the scroll complete
                    if checkbox.is_selected(): checkbox.click()
                except Exception as e:
                    self.logger.error(f"[{self.__class__.__name__}] Error processing row: {str(e)}")
                    continue

            ### 2. Now select only what we need...
            # NOTE: This block must come AFTER the above for loop bc it deselects all but the final project
            # Crash the program if this fails -- we have to have the the quizzes and exit tickets subtotals:
            try:
                # There are at least two with the same aria label because of fucking D2L...
                # The first is the label, so the last one should be the subtotal
                quizzes_subtotal_checkboxes = grade_table.find_elements(
                    By.CSS_SELECTOR,
                    f'input.d2l-checkbox[aria-label="Select {self.quizzes_category_label}"]'
                )
                quizzes_subtotal_checkbox = quizzes_subtotal_checkboxes[-1] # This one is the subtotal

                self.driver.execute_script("arguments[0].scrollIntoView(true);", quizzes_subtotal_checkbox)
                time.sleep(0.3)
                if not quizzes_subtotal_checkbox.is_selected(): quizzes_subtotal_checkbox.click()
                time.sleep(.3)

                ets_subtotal_checkboxes = grade_table.find_elements(
                    By.CSS_SELECTOR,
                    f'input.d2l-checkbox[aria-label="Select {self.exit_tickets_category_label}"]'
                )
                ets_subtotal_checkbox = ets_subtotal_checkboxes[-1] # This one is the subtotal

                self.driver.execute_script("arguments[0].scrollIntoView(true);", ets_subtotal_checkbox)
                time.sleep(0.3)
                if not ets_subtotal_checkbox.is_selected(): ets_subtotal_checkbox.click()
                time.sleep(.3)
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

            exit_tix_subtotal_numerator_idx = -1
            exit_tix_subtotal_denominator_idx = -1
            quizzes_subtotal_numerator_idx = -1
            quizzes_subtotal_denominator_idx = -1
            last_name_idx = -1
            first_name_idx = -1

            cols = list(df.columns)

            for i, col in enumerate(cols):
                colname = col.lower()
                if "numerator" in colname:
                    if "exit" in colname:
                        exit_tix_subtotal_numerator_idx = i
                    else:
                        quizzes_subtotal_numerator_idx = i
                elif "denominator" in colname:
                    if "exit" in colname:
                        exit_tix_subtotal_denominator_idx = i
                    else:
                        quizzes_subtotal_denominator_idx = i
                elif "last" in colname: # don't check for "name" since it is in username
                    first_name_idx = i
                elif "first" in colname:
                    last_name_idx = i

            df = df.rename(columns={
                cols[last_name_idx]: "Last_Name",
                cols[first_name_idx]: "First_Name",
                cols[exit_tix_subtotal_numerator_idx]: "exit_tickets_numerator",
                cols[exit_tix_subtotal_denominator_idx]: "exit_tickets_denominator",
                cols[quizzes_subtotal_numerator_idx]: "quizzes_numerator",
                cols[quizzes_subtotal_denominator_idx]: "quizzes_denominator"
            })

            # Reorder -- Put Username directly right of Email:
            other_cols = df.columns[:-1].tolist()
            new_column_order = other_cols[:4] + ["Username"] + other_cols[4:]
            df = df[new_column_order]

            cols = list(df.columns)

            # Fill nans with 0. DO NOT DROP nan data!!
            df['exit_tickets_numerator'] = df['exit_tickets_numerator'].fillna(0)
            df['exit_tickets_denominator'] = df['exit_tickets_denominator'].fillna(0)
            df['quizzes_numerator'] = df['quizzes_numerator'].fillna(0)
            df['quizzes_denominator'] = df['quizzes_denominator'].fillna(0)

            # Ensure numeric
            df = df.astype({'exit_tickets_numerator': float,
                            'exit_tickets_denominator': float,
                            'quizzes_numerator': float,
                            'quizzes_denominator': float})

            # Replace any 0s in denominator columns with mode (avert possibility of divide by zero)
            mode_series = df['exit_tickets_denominator'].mode()
            denom_mode = float(mode_series[0])
            df['exit_tickets_denominator'] = df['exit_tickets_denominator'].replace(0, denom_mode)

            mode_series = df['quizzes_denominator'].mode()
            denom_mode = float(mode_series[0])
            df['quizzes_denominator'] = df['quizzes_denominator'].replace(0, denom_mode)

            # Calculate new column: lab average (keep unrounded percentage)
            df['exit_tickets_average'] = (
                # Rounding for the way that digital exit tickets work (e.g., 49.999998333/50 points = full credit)
                100 * round((df['exit_tickets_numerator'] / df['exit_tickets_denominator']), 6)
            )

            df['quizzes_average'] = (
                100 * (df['quizzes_numerator'] / df['quizzes_denominator'])
            )
            # Append to list of all the lab sections' grades
            self.grades_dataframes_map[f"{course_name}_{ou}"] = df
            return True
        except Exception as e:
            self.logger.error(f"[{self.__class__.__name__}] Error parsing grade file data: {str(e)}")
            self.logger.debug(traceback.format_exc())
            return False

    def save_grades_to_db(self, semester: str = None):
        """Save lecture grades (quizzes and exit tickets) to database after scraping."""
        db = get_db()
        if not semester:
            semester = CURRENT_SEMESTER

        try:
            for course_ou, df in self.grades_dataframes_map.items():
                self.logger.info(f"Saving {len(df)} lecture records for {course_ou}")
                course_split = course_ou.split("_")
                course_name = course_split[0]
                ou = course_split[1]

                course_name_split = course_name.split("-")
                course_name = f"{course_name_split[0]}-{course_name_split[1]}"
                section = course_name_split[2]

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
                        quizzes_numerator=float(row.quizzes_numerator) if not pd.isna(row.quizzes_numerator) else 0.0,
                        quizzes_denominator=float(row.quizzes_denominator) if not pd.isna(row.quizzes_denominator) else 0.0,
                        quizzes_average=float(row.quizzes_average) if not pd.isna(row.quizzes_average) else 0.0,
                        exit_tickets_numerator=float(row.exit_tickets_numerator) if not pd.isna(row.exit_tickets_numerator) else 0.0,
                        exit_tickets_denominator=float(row.exit_tickets_denominator) if not pd.isna(row.exit_tickets_denominator) else 0.0,
                        exit_tickets_average=float(row.exit_tickets_average) if not pd.isna(row.exit_tickets_average) else 0.0,
                    )
                    db.add(snapshot)

                    # Update or create StudentGrade
                    student_grade = db.query(StudentGrade).filter_by(
                        student_id=org_id,
                        semester=semester,
                    ).first()

                    if not student_grade:
                        student_grade = StudentGrade(
                            student_id=org_id,
                            semester=semester
                        )
                        db.add(student_grade)

                    # Update lecture fields
                    student_grade.lecture_course = course
                    student_grade.quizzes_numerator = float(row.quizzes_numerator) if not pd.isna(row.quizzes_numerator) else 0.0
                    student_grade.quizzes_denominator = float(row.quizzes_denominator) if not pd.isna(row.quizzes_denominator) else 0.0
                    student_grade.quizzes_average = float(row.quizzes_average) if not pd.isna(row.quizzes_average) else 0.0
                    student_grade.exit_tickets_numerator = float(row.exit_tickets_numerator) if not pd.isna(row.exit_tickets_numerator) else 0.0
                    student_grade.exit_tickets_denominator = float(row.exit_tickets_denominator) if not pd.isna(row.exit_tickets_denominator) else 0.0
                    student_grade.exit_tickets_average = float(row.exit_tickets_average) if not pd.isna(row.exit_tickets_average) else 0.0

                    # Recalculate overall grades
                    student_grade.calculate_overall_grades()
                db.commit()
                self.logger.info(f"Successfully saved {course_name} lecture grades")
        except Exception as e:
            db.rollback()
            self.logger.error(f"Error saving to database: {str(e)}")
            raise
        finally:
            db.close()
