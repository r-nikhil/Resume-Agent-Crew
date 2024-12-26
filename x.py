from crewai import Agent, Crew, Process, Task 
from crewai.project import CrewBase, agent, crew, task, before_kickoff, after_kickoff
from crewai.tools import BaseTool
from crewai_tools import PDFSearchTool, ScrapeWebsiteTool, FileReadTool
from pydantic import BaseModel
from typing import List

class QualityOutput(BaseModel):
    quality_score: float
    suggestions: List[str]
    needs_revision: bool

class ThrallaBoysState(BaseModel):
    revision_count: int = 0
    max_revisions: int = 3
    latest_resume: str = ""
    quality_feedback: str = ""

@CrewBase
class ThrallaBoys():
    """ThrallaBoys crew. We help you professionally"""

    agents_config = 'config/agents.yaml'
    tasks_config = 'config/tasks.yaml'

    @before_kickoff
    def pull_data_example(self, inputs):
        print(f"Before kickoff function with inputs: {inputs}")
        return inputs

    @after_kickoff
    def log_results(self, output):
        print(f"Results: {output}")
        return output

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
            verbose=True
        )

    @task
    def analyze_resume_task(self) -> Task:
        return Task(
            config=self.tasks_config['analyze_resume_task']
        )

    @task
    def analyze_job_task(self) -> Task:
        return Task(
            config=self.tasks_config['analyze_job_task']
        )

    @task
    def optimize_resume_task(self) -> Task:
        return Task(
            config=self.tasks_config['optimize_resume_task'],
            output_file='report.md',
            output_pydantic=QualityOutput
        )

    @task
    def evaluate_resume_task(self) -> Task:
        return Task(
            config=self.tasks_config['evaluate_resume_task'],
            output_pydantic=QualityOutput
        )

    @crew
    def crew(self) -> Crew:
        """Creates the ThrallaBoys crew"""
        state = ThrallaBoysState()

        while state.revision_count < state.max_revisions:
            # Initial analysis tasks
            resume_analysis = self.analyze_resume_task().execute()
            job_analysis = self.analyze_job_task().execute()

            # First resume optimization
            if state.revision_count == 0:
                optimization_result = self.optimize_resume_task().execute()
                state.latest_resume = optimization_result.raw

            # Quality evaluation
            evaluation_result = self.evaluate_resume_task().execute()
            quality_output = evaluation_result.pydantic

            # Break if quality is satisfactory
            if not quality_output.needs_revision:
                print("Resume quality is satisfactory!")
                break

            # Increment revision count and check if we've hit the limit
            state.revision_count += 1
            if state.revision_count >= state.max_revisions:
                print("Maximum revision attempts reached.")
                break

            # Store feedback and trigger another optimization
            state.quality_feedback = "\n".join(quality_output.suggestions)
            print(f"Revision {state.revision_count}: Implementing quality feedback...")

            # Update the resume with new optimization
            optimization_result = self.optimize_resume_task().execute({
                "previous_feedback": state.quality_feedback,
                "previous_resume": state.latest_resume
            })
            state.latest_resume = optimization_result.raw

        return state.latest_resume