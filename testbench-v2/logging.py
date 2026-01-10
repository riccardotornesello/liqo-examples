import logging
from enum import Enum
from typing import Optional, List
from contextlib import contextmanager


class LogColors(str, Enum):
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


class StepStatus(str, Enum):
    """Status of a step or sub-step"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class Step:
    """Represents a step in the testbench process"""
    
    def __init__(self, name: str, indent_level: int = 0):
        self.name = name
        self.status = StepStatus.PENDING
        self.indent_level = indent_level
        self.substeps: List['Step'] = []
    
    def _get_status_icon(self) -> str:
        """Returns the emoji icon for the current status"""
        if self.status == StepStatus.COMPLETED:
            return "✅"
        elif self.status == StepStatus.IN_PROGRESS:
            return "ℹ️"
        elif self.status == StepStatus.FAILED:
            return "❌"
        else:  # PENDING
            return "⏳"
    
    def _get_indent(self) -> str:
        """Returns the indentation string based on indent level"""
        if self.indent_level == 0:
            return ""
        else:
            return "  " * self.indent_level + "- "
    
    def format_line(self) -> str:
        """Formats the step as a display line"""
        indent = self._get_indent()
        icon = self._get_status_icon()
        suffix = "..." if self.status == StepStatus.IN_PROGRESS else ""
        return f"{indent}{icon} {self.name}{suffix}"
    
    def add_substep(self, name: str) -> 'Step':
        """Adds a sub-step to this step"""
        substep = Step(name, self.indent_level + 1)
        self.substeps.append(substep)
        return substep


class StepLogger:
    """
    Logger for managing hierarchical steps and sub-steps in the testbench.
    
    Example usage:
        logger = StepLogger()
        
        # Simple step
        step1 = logger.add_step("Cluster A creato")
        logger.complete_step(step1)
        
        # Step with sub-steps
        step2 = logger.add_step("Creazione cluster B in corso")
        logger.start_step(step2)
        
        sub1 = step2.add_substep("Configurazione iniziale completata")
        logger.complete_step(sub1)
        
        sub2 = step2.add_substep("CNI installata")
        logger.complete_step(sub2)
        
        sub3 = step2.add_substep("Creazione risorse demo")
        logger.start_step(sub3)
        
        logger.display()
    """
    
    def __init__(self):
        self.steps: List[Step] = []
    
    def add_step(self, name: str) -> Step:
        """Adds a new main step"""
        step = Step(name, indent_level=0)
        self.steps.append(step)
        return step
    
    def start_step(self, step: Step):
        """Marks a step as in progress"""
        step.status = StepStatus.IN_PROGRESS
    
    def complete_step(self, step: Step):
        """Marks a step as completed"""
        step.status = StepStatus.COMPLETED
    
    def fail_step(self, step: Step):
        """Marks a step as failed"""
        step.status = StepStatus.FAILED
    
    def display(self):
        """Displays all steps and sub-steps with their current status"""
        for step in self.steps:
            print(step.format_line())
            for substep in step.substeps:
                print(substep.format_line())
    
    @contextmanager
    def step(self, name: str):
        """
        Context manager for automatic step management.
        
        Usage:
            logger = StepLogger()
            with logger.step("Creating cluster"):
                # Do work...
                pass
            # Step is automatically marked as completed
        """
        step = self.add_step(name)
        self.start_step(step)
        try:
            yield step
            self.complete_step(step)
        except Exception:
            # Intentionally catch all exceptions to mark step as failed
            # before re-raising to preserve the original error context
            self.fail_step(step)
            raise
    
    @contextmanager
    def substep(self, parent_step: Step, name: str):
        """
        Context manager for automatic sub-step management.
        
        Usage:
            logger = StepLogger()
            with logger.step("Creating cluster") as step:
                with logger.substep(step, "Installing CNI"):
                    # Do work...
                    pass
        """
        substep = parent_step.add_substep(name)
        self.start_step(substep)
        try:
            yield substep
            self.complete_step(substep)
        except Exception:
            # Intentionally catch all exceptions to mark step as failed
            # before re-raising to preserve the original error context
            self.fail_step(substep)
            raise


def log_info(message: str):
    logging.info(f"ℹ️ {LogColors.OKBLUE}INFO{LogColors.ENDC}\t{message}")


def log_success(message: str):
    logging.info(f"✅ {LogColors.OKGREEN}SUCCESS{LogColors.ENDC}\t{message}")


def log_warning(message: str):
    logging.warning(f"⚠️ {LogColors.WARNING}WARNING{LogColors.ENDC}\t{message}")


def log_error(message: str):
    logging.error(f"❌ {LogColors.FAIL}ERROR{LogColors.ENDC}\t{message}")
