from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.common.keys import Keys
from typing import Dict, List
from pathlib import Path
from datetime import datetime as dt
from database.models import *
from dotenv import load_dotenv
import traceback
import logging
import pandas as pd
import time
import random
import os


pd.options.mode.chained_assignment = None  # Suppresses warnings
# Initialize constants
CURRENT_SEMESTER = get_current_semester()
CURRENT_DIR = Path(os.path.dirname(os.path.abspath(__file__)))
# Load environment variables
load_dotenv((CURRENT_DIR / '.env').as_posix())

class D2LGradesScraper:
    def __init__(self, ous_list: List[str], downloads_dir: Path, headless: bool = False, webdriver_path: str = None):
        self.driver = None
        self.grades_dataframes_map = {} # Will store the coursename_ou and dataframe of each course section
        self.files_to_delete = []

        self.ous_list = ous_list
        self.webdriver_path = webdriver_path
        self.worker_id = os.getpid()

        self.downloads_dir = downloads_dir
        self.logging_dir = CURRENT_DIR / 'logs'
        os.makedirs(self.logging_dir, exist_ok=True)
        os.makedirs(self.downloads_dir, exist_ok=True)

        self.options = Options()
        if headless: self.options.add_argument('--headless')

        # Make browser appear more human-like
        self.options.set_preference("dom.webdriver.enabled", False)
        self.options.set_preference("useAutomationExtension", False)
        self.options.set_preference("navigator.webdriver", False)

        # Configure Firefox download preferences
        self.options.set_preference("browser.download.folderList", 2)  # Use custom directory
        self.options.set_preference("browser.download.dir", str(self.downloads_dir))
        self.options.set_preference("browser.download.manager.showWhenStarting", False)
        self.options.set_preference("browser.helperApps.neverAsk.saveToDisk",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    def setup_worker_logger(self):
        """Set up a logger for a specific worker"""
        class_name_short = f"{self.__class__.__name__}"[:4]
        logger = logging.getLogger(f'{self.__class__.__name__}_{self.worker_id}')
        logger.setLevel(logging.INFO)

        # Prevent duplicate handlers
        if logger.handlers:
            logger.handlers.clear()

        timestamp = dt.now().strftime("%m-%d-%Y_%H-%M")
        log_file = self.logging_dir / f'{class_name_short}_{timestamp}_{self.worker_id}.log'

        # File handler
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(
            logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        )

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(
            logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        )

        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

        return logger

    def start_browser(self):
        """Initialize the Firefox webdriver"""
        if self.webdriver_path:
            service = Service(self.webdriver_path)
            self.driver = webdriver.Firefox(service=service, options=self.options)
        else:
            self.driver = webdriver.Firefox(options=self.options)

    def login(self, username=os.getenv('MS_USERNAME'), password=os.getenv('MS_PWD')) -> bool:
        """
        Log into D2L using provided credentials or environment variables.
        Handles the Microsoft authentication flow.

        Args:
            username (str): ETSU username without @etsu.edu (default: from environment)
            password (str): ETSU password (default: from environment)

        Returns:
            bool: True if login successful, False otherwise
        """
        try:
            # Navigate directly to the SAML login URL instead of clicking the button
            self.driver.get("https://elearn.etsu.edu/d2l/lp/auth/saml/initiate-login?entityId=https%3A%2F%2Fsts.windows.net%2F962441d5-5055-4349-bad3-baec43c3d741%2F")

            wait = WebDriverWait(self.driver, 10)

            # Handle email input with multiple attempts
            email_field = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='email'][name='loginfmt']"))
            )
            wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "input[type='email'][name='loginfmt']"))
            )

            # Try direct input first
            try:
                email_field.send_keys(f"{username}@etsu.edu")
            except Exception as e:
                self.logger.warning(f"[{self.__class__.__name__}] Direct input failed, trying JavaScript: {str(e)}")
                self.driver.execute_script(
                    f"arguments[0].value = '{username}@etsu.edu';",
                    email_field
                )

            # Try to submit email with multiple methods
            try:
                email_field.send_keys(Keys.RETURN)
            except Exception as e:
                self.logger.warning(f"[{self.__class__.__name__}] Return key failed, trying next button: {str(e)}")
                next_button = wait.until(
                    EC.element_to_be_clickable((By.ID, "idSIButton9"))
                )
                next_button.click()

            # Handle password input
            time.sleep(2)  # Brief pause for page transition
            password_field = wait.until(
                EC.presence_of_element_located((By.NAME, "passwd"))
            )
            password_field.send_keys(password)

            # Submit password
            try:
                password_field.send_keys(Keys.RETURN)
            except Exception as e:
                self.logger.warning(f"[{self.__class__.__name__}] Return key failed for password, trying sign in button: {str(e)}")
                sign_in_button = wait.until(
                    EC.element_to_be_clickable((By.ID, "idSIButton9"))
                )
                sign_in_button.click()

            # Wait for successful D2L login
            wait.until(
                EC.url_contains("https://elearn.etsu.edu/d2l/home")
            )
            time.sleep(1)
            return True

        except Exception as e:
            self.logger.error(f"[{self.__class__.__name__}] D2L login flow failed: {str(e)}")
            self.logger.debug(traceback.format_exc())
            return False

    def set_calculation_options(self, ou: str) -> tuple[bool, str]:
        wait = WebDriverWait(self.driver, 10)
        course_name = ou
        try:
            # Navigate to the grade calculation options page
            self.driver.get(f"https://elearn.etsu.edu/d2l/lms/grades/admin/settings/calculation_options.d2l?d2l_isfromtab=1&ou={ou}")
            try:
                course_name_wrapper = wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, '.d2l-navigation-s-mobile-menu-title-bp'))
                )
                course_name = course_name_wrapper.find_element(By.CSS_SELECTOR, '.d2l-navigation-s-link')
                course_name = course_name.get_attribute("innerHTML")
                course_name = course_name.split(" -")[0]
            except Exception as e:
                self.logger.error(f"[{self.__class__.__name__}] Couldn't retrieve course name: {str(e)}")

            if self.modify_grade_calc_options:
                # First find the lable and use that to get the id (from the label's for property)
                # This approach is safer since the D2L bastards have changed Ids before.
                drop_ungraded_label = wait.until(
                    EC.presence_of_element_located((By.XPATH, "//label[contains(text(), 'Drop ungraded items')]"))
                )
                drop_ungraded_radio_input = wait.until(
                    EC.presence_of_element_located((By.ID, drop_ungraded_label.get_attribute("for")))
                )

                self.driver.execute_script("arguments[0].scrollIntoView();", drop_ungraded_radio_input)
                time.sleep(0.5)

                if self.drop_ungraded_items:
                    if not drop_ungraded_radio_input.is_selected():
                        self.logger.info("-> Select the drop ungraded button")
                        drop_ungraded_radio_input.click()
                else:
                    if drop_ungraded_radio_input.is_selected():
                        treat_ungraded_as_0_label = wait.until(
                            EC.presence_of_element_located((By.XPATH, "//label[contains(text(), 'Treat ungraded items as')]"))
                        )
                        treat_ungraded_as_0_radio_input = wait.until(
                            EC.presence_of_element_located((By.ID, treat_ungraded_as_0_label.get_attribute("for")))
                        )
                        print("-> Select the treat ungraded as 0 button")
                        treat_ungraded_as_0_radio_input.click()

                time.sleep(0.3)
                self.driver.execute_script("window.scrollTo(0, 0);")
                time.sleep(0.2)

                # Try clicking with explicit wait first
                wait.until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "d2l-floating-buttons"))
                )
                self.driver.execute_script("""
                    const containers = document.getElementsByTagName('d2l-floating-buttons');
                    // Get button from last container
                    const btns = containers[containers.length-1].getElementsByTagName('button');
                    // Loop thru btns; click save btn
                    Array.from(btns).forEach((element) => {
                        if (element.textContent.includes("Save")) {
                            element.click();
                        }
                    });
                """)
                wait.until(
                    EC.visibility_of_any_elements_located((By.CSS_SELECTOR, 'div[role="dialog"]'))
                )
                print("-> Click the save button and confirm button")
                self.driver.execute_script("""
                    // Now click the confirmation dialog
                    document.querySelector('div[role="dialog"]').querySelector('button.d2l-button[primary]').click();
                """)
                time.sleep(2)
            return True, course_name
        except Exception as e:
            self.logger.error(f"[{self.__class__.__name__}] Setting calculation options for {ou} failed: {str(e)}")
            self.logger.debug(traceback.format_exc())
            return False, course_name

    def _set_key_field_to_org_id(self):
        wait = WebDriverWait(self.driver, 10)
        key_field_label = wait.until(
            # Org Defined ID
            EC.presence_of_element_located((By.XPATH, "//label[contains(text(), 'Org')]"))
        )
        org_id_radio_input = wait.until(
            EC.presence_of_element_located((By.ID, key_field_label.get_attribute("for")))
        )
        self.driver.execute_script("arguments[0].scrollIntoView();", org_id_radio_input)
        time.sleep(0.2)

        if not org_id_radio_input.is_selected():
            org_id_radio_input.click()

    def _set_grade_values_to_points_grade(self):
        wait = WebDriverWait(self.driver, 10)
        points_grade_label = wait.until(
            # "Points grade" - Omitting capital letters in case some asshole changes the text case
            EC.presence_of_element_located((By.XPATH, "//label[contains(text(), 'oints')]"))
        )
        points_grade_checkbox = wait.until(
            EC.presence_of_element_located((By.ID, points_grade_label.get_attribute("for")))
        )
        self.driver.execute_script("arguments[0].scrollIntoView();", points_grade_checkbox)
        time.sleep(0.2)

        if not points_grade_checkbox.is_selected():
            self.logger.info(f"[{self.__class__.__name__}] Selecting Points grade checkbox...")
            points_grade_checkbox.click()

        # Omitting capital letters in case some asshole changes the text case
        grade_scheme_label = wait.until(
            # Grade Scheme:
            EC.presence_of_element_located((By.XPATH, "//label[contains(text(), 'cheme')]"))
        )
        grade_scheme_checkbox = wait.until(
            EC.presence_of_element_located((By.ID, grade_scheme_label.get_attribute("for")))
        )
        self.driver.execute_script("arguments[0].scrollIntoView();", grade_scheme_checkbox)
        time.sleep(0.2)

        # Deselect if it is selected
        if grade_scheme_checkbox.is_selected():
            self.logger.info(f"[{self.__class__.__name__}] Deselecting Grade Scheme checkbox...")
            points_grade_checkbox.click()

    def _select_all_user_details(self):
        wait = WebDriverWait(self.driver, 10)
        labels = ['Last Name', 'First Name', 'Email', 'Section Membership']
        for label in labels:
            try: # Wrapped in try/except, because I'm not sure if section membership label always there depending on D2L site setup
                label_element = wait.until(
                    EC.presence_of_element_located((By.XPATH, f"//label[contains(text(), '{label}')]"))
                )
                checkbox = wait.until(
                    EC.presence_of_element_located((By.ID, label_element.get_attribute("for")))
                )
                self.driver.execute_script("arguments[0].scrollIntoView();", checkbox)
                time.sleep(0.2)
                if not checkbox.is_selected():
                    self.logger.info(f"[{self.__class__.__name__}] Selecting {label} checkbox...")
                    checkbox.click()
                    time.sleep(0.1)
            except Exception as e:
                self.logger.info(f"[{self.__class__.__name__}] Error selecting {label}")
        time.sleep(0.5)

    def export_users_grades(self, ou: str) -> bool:
        """
        Navigate to the grade export page and configure the export options.
        """
        return True

    def get_csv_by_course_name(self, course_name: str):
        """Get the most recent .csv file in the specified directory."""
        # Get all csv files in the directory
        csv_files = list(self.downloads_dir.glob('*.csv'))
        if not csv_files:
            return None
        # Sort by creation time and get the most recent
        try:
            if not course_name.isnumeric(): # Testing to make sure it isn't the OU
                for file in csv_files:
                    if course_name in file.name:
                        self.files_to_delete.append(file.name)
                        return file
        except AttributeError:
            return None

    def parse_data_from_grades_csv(self, course_name: str, ou: str) -> bool:
        return True
    
    def scrape_all_ous(self) -> Dict[str, pd.DataFrame]:
        for ou in self.ous_list:
            time.sleep(random.uniform(0, .3))
            success, course_name = self.set_calculation_options(ou)
            if success:
                self.export_users_grades(ou)
                if not self.parse_data_from_grades_csv(course_name, ou):
                    # Repeat once
                    if not self.parse_data_from_grades_csv(course_name, ou):
                        self.logger.info(f"[{self.__class__.__name__}] {course_name}, {ou} -- two failed attempts to parse grades [skipped]")
                    else:
                       self.logger.info(f"[{self.__class__.__name__}] {course_name}, {ou} -- grades export successful")
                else:
                    self.logger.error(f"[{self.__class__.__name__}] {course_name}, {ou} -- grades export unsuccessful")
            else:
                self.logger.error(f"[{self.__class__.__name__}] {course_name}, {ou} -- scrape unsuccessful")

        return self.grades_dataframes_map

    def save_grades_to_db(self, semester: str = None):
        return None

    def close(self):
        """Close the browser and cleanup the files used"""
        if self.delete_downloads_on_completion:
            [ os.remove(self.downloads_dir / filename) for filename in self.files_to_delete ]

        if self.driver:
            self.driver.quit()

    def __enter__(self):
        """Context manager entry"""
        self.start_browser()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()