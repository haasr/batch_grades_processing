from scraping import OUScraper, LabGradesScraper, LectureGradesScraper
from workers import ChunkedWorkerPool
from pathlib import Path
from typing import List, Optional
import pandas as pd
import os

CURRENT_DIR = Path(os.path.dirname(os.path.abspath(__file__)))

# NOTE: Customize per semester as needed
def generate_lab_sections(inperson_start=1, inperson_end=42,
                        online_start=901, online_end=909):

    def _generate_lab_section(n: int) -> str:
        """Ensure 3-digit section code"""
        if n < 10: return f"CSCI-1150-00{n}" # generated in-person 001-009
        if n < 100: return f"CSCI-1150-0{n}" # generated in-person 010-099
        return f"CSCI-1150-{n}" # Already 3 digits (e.g., 201, 901)

    # Hard-coding since I don't have many 201 or 94x sections
    labs = ["CSCI-1150-940", "CSCI-1150-941", "CSCI-1150-942"]
    for i in range(inperson_start, inperson_end+1):
        labs.append(_generate_lab_section(i))
    for j in range(online_start, online_end+1):
        labs.append(_generate_lab_section(j))
    return labs

def scrape_ous(semester: str, labs: List[str], lectures: List[str], num_workers=2):
    """
    Find all the OUs of the current semester's lecture and lab D2L sites
    (necessary prerequisite for batch scraping their grades)
    """

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


def scrape_lab_grades(labs_name_ou_csv: Path, semester: str = '202580', num_workers=2):
    """
    Scrape lab grades in parallel, then save to database sequentially.

    This approach:
    - Scrapes in parallel (fast, no DB access)
    - Saves sequentially (slow but safe with SQLite)
    """
    sections_with_ous_df = pd.read_csv(labs_name_ou_csv)
    sections_with_ous_df = sections_with_ous_df.astype(str)

    sections_with_ous = dict(zip(sections_with_ous_df['Section'],
                                sections_with_ous_df['OU']))

    # Store all scrapers so we can save them later
    all_scrapers = []

    def scrape_labs_only(ous_list: List[str], headless: bool = True,webdriver_path: str = None):
        """Scrape grades but DON'T save to DB yet - just return the scraper."""
        scraper = LabGradesScraper(ous_list, headless=headless, webdriver_path=webdriver_path)
        scraper.start_browser()  # Start browser manually (not using 'with')
        scraper.login()
        lab_dataframes_map = scraper.scrape_all_ous()

        # DON'T call save_grades_to_db() here!
        # Just return the scraper with its populated dataframes
        print(f"========================== Worker scraped {len(ous_list)} sections ==========================")
        for section_name, df in lab_dataframes_map.items():
            print(f"  {section_name}: {len(df)} students")

        scraper.close()  # Close the browser and cleanup
        return scraper

    # Phase 1: Scrape in parallel (fast!)
    print("\n" + "="*80)
    print("PHASE 1: SCRAPING LAB GRADES IN PARALLEL")
    print("="*80)

    pool = ChunkedWorkerPool(
        items=list(sections_with_ous.values()),
        func=scrape_labs_only,
        func_args=(True,),
        num_workers=num_workers
    )
    scrapers = pool.run()  # Returns list of scrapers with their dataframes

    # Phase 2: Save sequentially (safe!)
    print("\n" + "="*80)
    print("PHASE 2: SAVING TO DATABASE (SEQUENTIAL)")
    print("="*80)

    for idx, scraper in enumerate(scrapers, 1):
        print(f"\nSaving scraper {idx}/{len(scrapers)}...")
        try:
            scraper.save_grades_to_db(semester=semester)
            print(f"✓ Saved scraper {idx} successfully")
        except Exception as e:
            print(f"✗ Error saving scraper {idx}: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "="*80)
    print("LAB GRADES COMPLETE")
    print("="*80)


def scrape_lecture_grades(lecture_ous: List[str], semester: str = '202580',
                          num_workers=2):
    """
    Scrape lecture grades in parallel, then save to database sequentially.

    This approach:
    - Scrapes in parallel (fast, no DB access)
    - Saves sequentially (slow but safe with SQLite)
    """

    def scrape_lectures_only(ous_list: List[str], headless: bool = True, webdriver_path: str = None):
        """Scrape grades but DON'T save to DB yet - just return the scraper."""
        scraper = LectureGradesScraper(ous_list, headless=headless, webdriver_path=webdriver_path)
        scraper.start_browser()  # Start browser manually (not using 'with')
        scraper.login()
        lecture_dataframes_map = scraper.scrape_all_ous()

        # DON'T call save_grades_to_db() here!
        # Just return the scraper with its populated dataframes

        print(f"========================== Worker scraped {len(ous_list)} sections ==========================")
        for section_name, df in lecture_dataframes_map.items():
            print(f"  {section_name}: {len(df)} students")

        scraper.close()  # Close the browser and cleanup
        return scraper

    # Phase 1: Scrape in parallel (fast!)
    print("\n" + "="*80)
    print("PHASE 1: SCRAPING LECTURE GRADES IN PARALLEL")
    print("="*80)

    pool = ChunkedWorkerPool(
        items=lecture_ous,
        func=scrape_lectures_only,
        func_args=(True,),
        num_workers=num_workers
    )
    scrapers = pool.run()  # Returns list of scrapers with their dataframes

    # Phase 2: Save sequentially (safe!)
    print("\n" + "="*80)
    print("PHASE 2: SAVING TO DATABASE (SEQUENTIAL)")
    print("="*80)

    for idx, scraper in enumerate(scrapers, 1):
        print(f"\nSaving scraper {idx}/{len(scrapers)}...")
        try:
            scraper.save_grades_to_db(semester=semester)
            print(f"✓ Saved scraper {idx} successfully")
        except Exception as e:
            print(f"✗ Error saving scraper {idx}: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "="*80)
    print("LECTURE GRADES COMPLETE")
    print("="*80)


def main():
    '''
    Expected CSV file format for the scrape_lab_grades function:

    Section,OU
    CSCI-1150-001,10331755
    CSCI-1150-002,10331809
    ...

    the first column is the human-readable course names so you know
    what D2L sites each of these OUs map to. It doesn't actually get
    used at all in the scraping logic. It's just for personal sanity
    if you ever look at your CSV file and don't know what the hell
    the OUs are.
    '''
    ########## Common variables used across all scraping functions ##########
    semester = '202580' # 80 = Fall, 10 = Spring, 50 = Summer
    num_workers = 2
    # CONSIDERATIONS FOR NUMBER OF WORKERS, FAILED SCRAPE JOBS:
    # Customize how many workers will scrape in parallel.
    # 2 means the list of OUs/courses to scrape is divided up between 2 workers who work in parallel
    # so two Firefox windows will be opened and scraped simultaneously. While each worker has another
    # OU in the list to process, it will keep on scraping and close when it has finished all the items
    # in the list that it was assigned (half the classes when 2 workers, 1/3rd when 3 workers, etc.).
    #
    #  With a Ryzen 7 or Core i7/i9, you may be able to smoothly handle 3 Firefox windows at a time.
    # Increasing the sleep time between actions in the scraper classes can also mitigate failed scrapes if you're
    # finding lots of failed scrapes. With 2 workers on my Ryzen 5, it failed to scrape one section out of 54.
    #
    #  When a section's scrape fails as a one-off, just edit the list of OUs you pass to the method to only
    # include the failed jobs and run it again. No need to start all over.


    ########## Variables for OU scraping ###########
    # Pass the course names of labs and lectures as lists. The OUScraper's job is to
    # build a find all those course sites and print their OUs so you can store the OUs
    # to a list (see expected CSV file format comment at top of main method).
    # (necessary precondition before you can scrape the lecture and lab sites because
    # the are accessed in URLs by their OUs):
    lab_names = generate_lab_sections() # Or replace with list
    lecture_names = ["CSCI-1100-001", "CSCI-1100-901"]

    ########## Variables for lab scraping ##########
    labs_name_ou_csv = "labs_ou_202580.csv"

    ######## Variables for lecture scraping ########
    lecture_ous = ['10219691', '10219784'] # Didn't use CSV format since I only have 2 major (merged) lecture sites to scrape

    #------------ Scraping functions ------------ #
    # Uncomment what you what to run:
    #scrape_ous(semester, lab_names, lecture_names, num_workers)
    #scrape_lab_grades(CURRENT_DIR / labs_name_ou_csv, semester, num_workers)
    #scrape_lecture_grades(lecture_ous, semester, num_workers)

if __name__ == '__main__':
    main()