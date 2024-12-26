from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai_tools import FileReadTool, ScrapeWebsiteTool

@CrewBase
class ThrallaBoys():
		"""ThrallaBoys crew. We help you professionally"""
		agents_config = 'config/agents.yaml'
		tasks_config = 'config/tasks.yaml'

		@agent
		def resume_analyzer(self) -> Agent:
				return Agent(
						config=self.agents_config['resume_analyzer'],
						tools=[FileReadTool()],
						verbose=True
				)

		@agent
		def job_analyzer(self) -> Agent:
				return Agent(
						config=self.agents_config['job_analyzer'],
						tools=[ScrapeWebsiteTool()],
						verbose=True
				)

		@agent
		def resume_writer(self) -> Agent:
				return Agent(
						config=self.agents_config["resume_writer"],
						verbose=True
				)

		@agent
		def quality_controller(self) -> Agent:
				return Agent(
						config=self.agents_config["quality_controller"],
						verbose=True,
						allow_delegation=True
				)

		@task
		def analyze_resume_task(self) -> Task:
				return Task(
						config=self.tasks_config['analyze_resume_task'],
						output_file='temp/original_resume_analysis.txt',
						agent=self.resume_analyzer()
				)

		@task 
		def analyze_job_task(self) -> Task:
				return Task(
						config=self.tasks_config['analyze_job_task'],
						output_file='temp/job_analysis.txt',
						agent=self.job_analyzer()
				)

		@task
		def optimize_resume_task(self) -> Task:
				return Task(
						config=self.tasks_config['optimize_resume_task'],
						output_file='temp/optimized_resume.md',
						agent=self.resume_writer(),
						context=[
								self.analyze_resume_task(),
								self.analyze_job_task()
						]
				)

		@task
		def evaluate_resume_task(self) -> Task:
				return Task(
						config=self.tasks_config['evaluate_resume_task'],
						output_file='temp/evaluation.txt',
						agent=self.quality_controller(),
						context=[
								self.analyze_resume_task(),
								self.analyze_job_task(),
								self.optimize_resume_task()
						]
				)

		@crew
		def crew(self) -> Crew:
				"""Creates the ThrallaBoys crew"""
				return Crew(
						agents=[
								self.resume_analyzer(),
								self.job_analyzer(),
								self.resume_writer()
						],
						tasks=[
								self.analyze_resume_task(),
								self.analyze_job_task(),
								self.optimize_resume_task(),
								self.evaluate_resume_task()
						],
						process=Process.hierarchical,
						manager_agent=self.quality_controller(),
						verbose=True,
						max_iter=3
				)