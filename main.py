import tkinter as tk
from tkinter import simpledialog, messagebox, Scrollbar, Canvas, filedialog
import pandas as pd
import requests
import matplotlib.pyplot as plt
from bs4 import BeautifulSoup
import unittest
import os
from unittest.mock import MagicMock
import threading



class SalaryEstimator:
    """Estimates salary ranges based on job titles and web scraping."""

    def __init__(self):
        self.salary_data = {}  # Cache salary data (job title: range)

    def estimate_salary(self, job_title):
        if job_title not in self.salary_data:
            salary_range = self.scrape_salary_web(job_title)
            self.salary_data[job_title] = salary_range
        return self.salary_data.get(job_title, "Salary not available")

    def scrape_salary_web(self, job_title):
        try:
            url = f"https://www.indeed.com/cmp/salary/{job_title}"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, "html.parser")
            salary_tag = soup.find("span", class_="salary-snippet")
            if salary_tag:
                salary_text = salary_tag.text.strip()
                return salary_text
            else:
                return "Salary not found"
        except requests.RequestException as e:
            return f"Error fetching salary: {e}"


class Job:
    def __init__(self, file_path):
        try:
            self.Job_File = pd.read_csv(file_path)
        except FileNotFoundError:
            messagebox.showerror("File Error", f"File not found: {file_path}")
            self.Job_File = pd.DataFrame()

    def search_jobs(self, user_input):
        if self.Job_File.empty:
            return []
        jobs = self.Job_File.iloc[:, -8]
        store_jobs = []
        usplit = user_input.lower().split()
        for index, job_title in jobs.items():
            if isinstance(job_title, str):
                job_title_split = job_title.lower().split()
                if any(word in job_title_split for word in usplit):
                    store_jobs.append((index, job_title))
        return store_jobs

    def get_job_details(self, index):
        try:
            description = self.Job_File.iloc[index, self.Job_File.columns.get_loc("description1")]
            skills = self.Job_File.iloc[index, self.Job_File.columns.get_loc("skills req.")]
            return description, skills
        except KeyError:
            return "Description not available", "Skills not available"


class Api:
    def __init__(self, job_instance):
        self.job = job_instance
        self.salary_estimator = SalaryEstimator()

    def import_Api(self, user_input):
        api_key = os.getenv('RAPIDAPI_KEY')
        if not api_key:
            messagebox.showerror("API Key Error",
                                 "API key not found. Please set the RAPIDAPI_KEY environment variable.")
            return

        url = "https://jsearch.p.rapidapi.com/search"
        querystring = {"query": f"{user_input} in canada", "page": "1", "num_pages": "1"}
        headers = {
            "X-RapidAPI-Key": api_key,
            "X-RapidAPI-Host": "jsearch.p.rapidapi.com"
        }
        try:
            response = requests.get(url, headers=headers, params=querystring, timeout=10)
            response.raise_for_status()
            data = response.json()

            if 'data' in data and data['data']:
                len_data = len(data['data'])
                num_jobs = simpledialog.askinteger("Number of Jobs",
                                                   f"We found {len_data} jobs. How many do you want to see?",
                                                   minvalue=1, maxvalue=len_data)
                if num_jobs is None:
                    return

                job_details = []
                for job in data['data'][:num_jobs]:
                    job_title = job.get('job_title', 'Title not available')
                    job_description = job.get('job_description', 'Description not available')
                    job_apply_link = job.get('job_apply_link', 'Apply link not available')
                    job_city = job.get('job_city', 'City not available')
                    salary_estimate = self.salary_estimator.estimate_salary(job_title)

                    job_details.append(f"Title: {job_title}\n"
                                       f"Description: {job_description}\n"
                                       f"Salary Estimate: {salary_estimate}\n"
                                       f"Apply Link: {job_apply_link}\n"
                                       f"City: {job_city}\n\n")

                display_text = "\n".join(job_details)
                self.show_scrollable_text("Top Jobs from API", display_text)

                self.plot_demand_graph(data['data'])
            else:
                messagebox.showinfo("No Jobs Found", "No jobs were found for your query.")

        except requests.RequestException as e:
            messagebox.showerror("API Error", f"An error occurred while fetching data: {e}")

    def plot_demand_graph(self, job_data):
        if job_data:
            job_titles = [job['job_title'] for job in job_data][:8]
            job_openings_high = [10000, 8000, 12000, 6000, 9000, 4000, 7000, 9000]  # Placeholder data

            plt.figure(figsize=(10, 6))
            plt.plot(job_titles, job_openings_high, marker='o', color='blue', linestyle='-',
                     label='Highly Demanded Jobs')
            plt.xlabel('Occupations')
            plt.ylabel('Number of Job Openings')
            plt.title('Job Openings by Occupation')
            plt.xticks(rotation=45)
            plt.legend()
            plt.grid()
            plt.tight_layout()
            plt.show()

    def show_scrollable_text(self, title, text):
        scrollable_window = tk.Toplevel()
        scrollable_window.title(title)

        canvas = Canvas(scrollable_window)
        scrollbar = Scrollbar(scrollable_window, orient="vertical", command=canvas.yview)
        text_frame = tk.Frame(canvas)

        canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        canvas.create_window((0, 0), window=text_frame, anchor="nw")

        def configure_frame(event):
            canvas.configure(scrollregion=canvas.bbox("all"))

        text_frame.bind("<Configure>", configure_frame)

        text_label = tk.Label(text_frame, text=text, justify="left", anchor="w", wraplength=750)
        text_label.pack(fill="both", expand=True)


class JobSearchApp:
    def __init__(self, master):
        self.master = master
        master.title("Job Search App")

        self.label = tk.Label(master, text="Search For A Job:")
        self.label.pack()

        self.entry = tk.Entry(master)
        self.entry.pack()

        self.search_button = tk.Button(master, text="Search My Data", command=self.search_my_data)
        self.search_button.pack()

        self.api_search_button = tk.Button(master, text="Search at API", command=self.search_at_api)
        self.api_search_button.pack()

        self.sort_button = tk.Button(master, text="Sort by Title", command=self.bubble_sort)
        self.sort_button.pack()

        self.results_text = tk.Text(master, height=10, width=50)
        self.results_text.pack()

        self.select_label = tk.Label(master, text="Enter the number of the job to view details:")
        self.select_label.pack()

        self.selection_entry = tk.Entry(master)
        self.selection_entry.pack()

        self.view_button = tk.Button(master, text="View Details", command=self.view_details)
        self.view_button.pack()

        # File selection
        self.file_button = tk.Button(master, text="Select Job CSV File", command=self.select_file)
        self.file_button.pack()

        self.job = None
        self.api_job = None
        self.store_jobs = []

    def select_file(self):
        file_path = filedialog.askopenfilename(title="Select Job CSV File", filetypes=(("CSV Files", "*.csv"),))
        if file_path:
            self.job = Job(file_path)
            self.api_job = Api(self.job)
            messagebox.showinfo("File Selected", f"Selected file: {file_path}")

    def search_my_data(self):
        if not self.job:
            messagebox.showwarning("No File", "Please select a job CSV file first.")
            return
        user_input = self.entry.get().lower()
        self.store_jobs = self.job.search_jobs(user_input)
        if self.store_jobs:
            self.display_jobs()
        else:
            messagebox.showinfo("Unavailable", "This job is currently unavailable in our data.")

    def search_at_api(self):
        if not self.api_job:
            messagebox.showwarning("No File", "Please select a job CSV file first.")
            return
        user_input = self.entry.get().lower()
        thread = threading.Thread(target=self.api_job.import_Api, args=(user_input,))
        thread.start()

    def bubble_sort(self):
        self.store_jobs = sorted(self.store_jobs, key=lambda x: x[1].lower())
        self.display_jobs()

    def display_jobs(self):
        self.results_text.delete(1.0, tk.END)
        for count, job_info in enumerate(self.store_jobs, start=1):
            index, job_title = job_info
            self.results_text.insert(tk.END, f"{count} - {job_title}\n")

    def view_details(self):
        selection = self.selection_entry.get()
        try:
            selection_index = int(selection) - 1
            if 0 <= selection_index < len(self.store_jobs):
                index, job_title = self.store_jobs[selection_index]
                description, skills = self.job.get_job_details(int(index))
                messagebox.showinfo("Job Details",
                                    f"Title: {job_title}\nDescription: {description}\nSkills Required: {skills}")
            else:
                messagebox.showerror("Invalid Selection", "Please enter a valid job number.")
        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter a valid number.")


class TestJobSearchApp(unittest.TestCase):
    def setUp(self):
        # Initialize Tkinter without opening a window
        self.root = tk.Tk()
        self.root.withdraw()
        self.app = JobSearchApp(self.root)
        self.app.job = MagicMock()
        self.app.api_job = MagicMock()

    def tearDown(self):
        self.root.update()
        self.root.destroy()

    def test_search_my_data(self):
        self.app.job.search_jobs.return_value = [(0, "Software Engineer")]
        self.app.display_jobs = MagicMock()
        self.app.entry.insert(tk.END, "software engineer")

        self.app.search_my_data()

        self.app.job.search_jobs.assert_called_with("software engineer")
        self.app.display_jobs.assert_called()

    def test_search_at_api(self):
        self.app.api_job.import_Api = MagicMock()
        self.app.entry.insert(tk.END, "software engineer")

        self.app.search_at_api()

        self.app.api_job.import_Api.assert_called_with("software engineer")

    def test_bubble_sort(self):
        self.app.store_jobs = [(0, "Software Engineer"), (1, "Data Scientist"), (2, "Web Developer")]
        self.app.bubble_sort()
        expected = [(1, "Data Scientist"), (0, "Software Engineer"), (2, "Web Developer")]
        self.assertEqual(self.app.store_jobs, expected)

    def test_view_details(self):
        self.app.job.get_job_details.return_value = ("Job Description", "Skills")
        self.app.store_jobs = [(0, "Software Engineer")]
        self.app.selection_entry.insert(tk.END, "1")

        # Mock messagebox to prevent actual popup
        messagebox.showinfo = MagicMock()

        self.app.view_details()

        self.app.job.get_job_details.assert_called_with(0)
        messagebox.showinfo.assert_called_with(
            "Job Details",
            "Title: Software Engineer\nDescription: Job Description\nSkills Required: Skills"
        )


if __name__ == '__main__':
    import sys
    import threading

    if 'test' in sys.argv:
        unittest.main(argv=[sys.argv[0]])
    else:
        root = tk.Tk()
        app = JobSearchApp(root)
        root.mainloop()
