from scraping import OUScraper, LabGradesScraper, LectureGradesScraper
from workers import ChunkedWorkerPool
from pathlib import Path
from typing import List
import pandas as pd
import os

CURRENT_DIR = Path(os.path.dirname(os.path.abspath(__file__)))

def scrape_ous(semester: str):
    """
    Find all the OUs of the current semester's lecture and lab D2L sites
    (necessary prerequisite for batch scraping their grades)
    """
    def generate_lab_section(n: int) -> str:
        """Ensure 3-digit section code"""
        if n < 10: return f"CSCI-1150-00{n}" # generated in-person 001-009
        if n < 100: return f"CSCI-1150-0{n}" # generated in-person 010-099
        return f"CSCI-1150-{n}" # Already 3 digits (e.g., 201, 901)

    def generate_lab_sections(inperson_start=1, inperson_end=42,
                            online_start=901, online_end=909):
        # Hard-coding since I don't have many 201 or 94x sections
        labs = ["CSCI-1150-940", "CSCI-1150-941", "CSCI-1150-942"]
        for i in range(inperson_start, inperson_end+1):
            labs.append(generate_lab_section(i))
        for j in range(online_start, online_end+1):
            labs.append(generate_lab_section(j))
        return labs

    labs = generate_lab_sections()
    lectures = ["CSCI-1100-001", "CSCI-1100-901"]

    def scrape_class_ous(classes: List[str], semester: str,
                        headless: bool = True, webdriver_path: str = None):
        with OUScraper(classes, semester, headless=headless,
                    webdriver_path=webdriver_path) as scraper:
            scraper.login()
            scraper.search_classes()
            print("\nOUs:")
            for k, v in scraper.ou_map.items():
                print(f"{k},{v}")

    pool = ChunkedWorkerPool(items=labs, func=scrape_class_ous,
                            func_args=(semester, True), num_workers=2)
    results = pool.run()
    print("\nLabs results:", results)

    pool = ChunkedWorkerPool(items=lectures, func=scrape_class_ous,
                            func_args=(semester, True), num_workers=1)
    results = pool.run()
    print("\nLectures results:", results)

def scrape_lab_grades(labs_name_ou_csv: Path):
    sections_with_ous_df = pd.read_csv(labs_name_ou_csv)
    sections_with_ous_df = sections_with_ous_df.astype(str)

    sections_with_ous = dict(zip(sections_with_ous_df['Section'],
                                sections_with_ous_df['OU']))

    def scrape_labs(ous_list: List[str], headless: bool = True, webdriver_path: str = None):
        with LabGradesScraper(ous_list, headless=headless, webdriver_path=webdriver_path) as scraper:
            scraper.login()
            lab_dataframes_map = scraper.scrape_all_ous()
            scraper.save_grades_to_db()

            print("========================== DataFrames created ==========================")
            for section_name, df in lab_dataframes_map.items():
                print(f"\n------------------------ {section_name} ------------------------")
                print(df.head(5))
                df.to_csv("lab_grades.csv")

    pool = ChunkedWorkerPool(items=list(sections_with_ous.values())[:2], # Just testing with a few
                            func=scrape_labs, func_args=(True,), num_workers=2)
    results = pool.run()
    print("========================== Scraping results ==========================")
    print(results)

def scrape_lecture_grades(lecture_ous: List[str]):
    def scrape_lectures(ous_list: List[str], headless: bool = True, webdriver_path: str = None):
        with LectureGradesScraper(ous_list, headless=headless, webdriver_path=webdriver_path) as scraper:
            scraper.login()
            lecture_dataframes_map = scraper.scrape_all_ous()
            scraper.save_grades_to_db()

            print("========================== DataFrames created ==========================")
            for section_name, df in lecture_dataframes_map.items():
                print(f"\n------------------------ {section_name} ------------------------")
                print(df.head(5))
                df.to_csv("lecture_grades.csv")

    pool = ChunkedWorkerPool(items=lecture_ous, func=scrape_lectures,
                            func_args=(True,), num_workers=2)
    results = pool.run()
    print("========================== Scraping results ==========================")
    print(results)

def main():
    # 80 = Fall, 10 = Spring, 50 = Summer
    semester='202580'
    #scrape_ous(semester)
    labs_name_ou_csv = 'labs_ou_202580.csv'
    scrape_lab_grades(CURRENT_DIR / labs_name_ou_csv)
    scrape_lecture_grades(['10219699', '10219787'])

if __name__ == '__main__':
    main()