"""
Task scheduling system for VayuAPI
Supports cron-style and interval-based scheduling
"""

import asyncio
from typing import Callable, Dict, List, Optional
from datetime import datetime, timedelta
import time


class Task:
    """
    Scheduled task definition.
    """

    def __init__(
        self,
        func: Callable,
        interval: Optional[int] = None,
        cron: Optional[str] = None,
        name: str = None
    ):
        self.func = func
        self.interval = interval  # seconds
        self.cron = cron
        self.name = name or func.__name__
        self.last_run = None
        self.next_run = None
        self.running = False

    def should_run(self) -> bool:
        """Check if task should run now."""
        if self.interval:
            if self.last_run is None:
                return True
            return time.time() - self.last_run >= self.interval
        elif self.cron:
            return self._check_cron()
        return False

    def _check_cron(self) -> bool:
        """Check if cron schedule matches current time."""
        # Simplified cron parsing
        # Format: "minute hour day month day_of_week"
        # Example: "0 0 * * *" = daily at midnight
        if not self.cron:
            return False

        now = datetime.now()
        parts = self.cron.split()

        if len(parts) != 5:
            return False

        minute, hour, day, month, day_of_week = parts

        # Check each component
        if minute != '*' and int(minute) != now.minute:
            return False
        if hour != '*' and int(hour) != now.hour:
            return False
        if day != '*' and int(day) != now.day:
            return False
        if month != '*' and int(month) != now.month:
            return False

        return True

    async def run(self):
        """Execute the task."""
        self.running = True
        self.last_run = time.time()

        try:
            if asyncio.iscoroutinefunction(self.func):
                await self.func()
            else:
                self.func()
        except Exception as e:
            print(f"Error running task {self.name}: {e}")
        finally:
            self.running = False


class TaskScheduler:
    """
    Task scheduler for running periodic and cron-based tasks.

    Example:
        ```python
        from vayuapi.scheduler import TaskScheduler

        scheduler = TaskScheduler()

        # Interval-based task
        @scheduler.task(interval=60)
        async def cleanup():
            print("Running cleanup...")

        # Cron-based task
        @scheduler.cron("0 0 * * *")  # Daily at midnight
        async def daily_report():
            print("Generating daily report...")

        # Start scheduler
        await scheduler.start()
        ```
    """

    def __init__(self):
        self.tasks: Dict[str, Task] = {}
        self._running = False
        self._loop_task = None

    def task(self, interval: int = None, cron: str = None, name: str = None):
        """
        Decorator for registering scheduled tasks.

        Args:
            interval: Run every N seconds
            cron: Cron expression for scheduling
            name: Task name
        """
        def decorator(func: Callable):
            task = Task(func, interval=interval, cron=cron, name=name)
            self.tasks[task.name] = task
            return func
        return decorator

    def cron(self, expression: str, name: str = None):
        """
        Decorator for cron-based tasks.

        Args:
            expression: Cron expression
            name: Task name
        """
        return self.task(cron=expression, name=name)

    def add_task(
        self,
        func: Callable,
        interval: int = None,
        cron: str = None,
        schedule: str = None,
        name: str = None
    ):
        """
        Manually add a task.

        Args:
            func: Function to execute
            interval: Run every N seconds
            cron: Cron expression (or use schedule parameter)
            schedule: Alias for cron parameter
            name: Task name
        """
        # Support both 'cron' and 'schedule' parameters
        cron_expr = schedule if schedule is not None else cron
        task = Task(func, interval=interval, cron=cron_expr, name=name)
        self.tasks[task.name] = task

    def remove_task(self, name: str):
        """Remove a task by name."""
        if name in self.tasks:
            del self.tasks[name]

    async def start(self):
        """Start the scheduler."""
        self._running = True
        self._loop_task = asyncio.create_task(self._run_loop())

    async def stop(self):
        """Stop the scheduler."""
        self._running = False
        if self._loop_task:
            self._loop_task.cancel()
            try:
                await self._loop_task
            except asyncio.CancelledError:
                pass

    async def _run_loop(self):
        """Main scheduler loop."""
        while self._running:
            try:
                # Check all tasks
                for task in self.tasks.values():
                    if task.should_run() and not task.running:
                        # Run task in background
                        asyncio.create_task(task.run())

                # Sleep for a short interval
                await asyncio.sleep(1)
            except Exception as e:
                print(f"Scheduler error: {e}")

    def get_task_status(self) -> Dict:
        """Get status of all tasks."""
        return {
            name: {
                "running": task.running,
                "last_run": task.last_run,
                "interval": task.interval,
                "cron": task.cron,
            }
            for name, task in self.tasks.items()
        }


# Global scheduler instance
scheduler = TaskScheduler()


# Convenient shortcuts
def schedule_task(interval: int = None, cron: str = None, name: str = None):
    """Shortcut for scheduling tasks."""
    return scheduler.task(interval=interval, cron=cron, name=name)


def schedule_cron(expression: str, name: str = None):
    """Shortcut for cron-based tasks."""
    return scheduler.cron(expression=expression, name=name)
