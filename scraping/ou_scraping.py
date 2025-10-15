from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.common.keys import Keys
from pathlib import Path
from datetime import datetime as dt
from dotenv import load_dotenv
from typing import List
import traceback
import logging
import time
import re
import os

# Configure logging
CURRENT_DIR = Path(os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
load_dotenv((CURRENT_DIR / '.env').as_posix())

class OUScraper:
    def __init__(
            self,
            classes: List[str],
            semester: str,
            headless: bool = True,
            webdriver_path: str = None
        ):
        self.semester = semester
        self.classes = classes
        self.driver = None
        self.webdriver_path = webdriver_path
        
        # Dictionary to hold the site name and its OU
        self.ou_map = {}

        self.worker_id = os.getpid()
        self.logging_dir = CURRENT_DIR / 'logs'
        # Added these as required params so I don't forget that the order matters
        # (e.g., first assign worker id and logging dir to self)
        self.logger = self.setup_worker_logger(self.logging_dir, self.worker_id)

        self.options = Options()
        if headless: self.options.add_argument('--headless')

    def setup_worker_logger(self, logging_dir: Path, worker_id: int):
        """Set up a logger for a specific worker"""
        os.makedirs(logging_dir, exist_ok=True)

        logger = logging.getLogger(f'OUScraper_{worker_id}')
        logger.setLevel(logging.INFO)

        # Prevent duplicate handlers
        if logger.handlers:
            logger.handlers.clear()

        timestamp = dt.now().strftime("%m-%d-%Y_%H-%M")
        log_file = logging_dir / f'ou_{timestamp}_{self.worker_id}.log'

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

        self.logger.info(f"Assigned self.driver = {self.driver}")
        
    def login(self, username=os.getenv('MS_USERNAME'), password=os.getenv('MS_PWD')):
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

    def search_classes(self):
        def _get_ou(scraper, regex_pattern):
            try:
                item_names = scraper.find_elements(By.CSS_SELECTOR, ".d2l-course-selector-item-name")
                self.logger.debug(f"Searched results: {item_names}")
                for item in item_names:
                    link = item.find_element(By.TAG_NAME, "a")
                    label = link.get_attribute("innerHTML") # Use inner HTML since aria label can be empty
                    if label and re.match(r"%s" % regex_pattern, label):
                        href = link.get_attribute("href")
                        self.logger.debug(f"-> href of search result: {href}")
                        return href.split('/')[-1].strip()
                return None  # Return None if no match is found
            except Exception as e:
                print(f"An error occurred: {e}")
                return None

        def _get_classes_grid_button():
            wait = WebDriverWait(self.driver, 10)
            return wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'd2l-labs-navigation-dropdown-button-icon[icon="tier3:classes"]'))
            )

        def _click_search_button():
            self.driver.execute_script("""
                document.getElementsByTagName('d2l-input-search')[0].shadowRoot.querySelector('d2l-button-icon').click();
            """)
            time.sleep(.5)

        def _search_classes(classes: List[str], ou_strings: dict):
            self.logger.debug(f"[{self.__class__.__name__}] Searching courses...")
            wait = WebDriverWait(self.driver, 10)
            for course in classes:
                course_cleaned = course.strip().upper()
                self.logger.debug(f"> Searching course {course_cleaned} {self.semester}")

                classes_search_grid_btn = _get_classes_grid_button()
                classes_search_grid_btn.click()
                time.sleep(.6)

                # Search the current course name with the current semester string
                self.driver.execute_script(f"""
                    const input = document.getElementsByTagName('d2l-input-search')[0];
                    input.value = `{course_cleaned} {self.semester}`;
                """)

                time.sleep(1)
                _click_search_button()

                # Click matching OU if it exists
                courses_search_section = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '.d2l-course-selector-item')))
                regex = f"\\s*{course_cleaned}.*\\s*{self.semester}"
                ou = _get_ou(courses_search_section, regex)

                if ou:
                    self.logger.info(f"+ Course {course_cleaned} was found with OU={ou}")
                    ou_strings[ou] = course_cleaned
                else:
                    self.logger.info(f"- Course {course_cleaned} not found")

        _search_classes(self.classes, self.ou_map)

    def close(self):
        """Close the browser and cleanup"""
        if self.driver:
            self.driver.quit()

    def __enter__(self):
        """Context manager entry"""
        self.start_browser()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
