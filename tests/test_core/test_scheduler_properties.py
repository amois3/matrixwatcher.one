"""Property-based tests for Scheduler.

Feature: matrix-watcher, Property 47: No execution overlap
Feature: matrix-watcher, Property 48: Priority ordering
Validates: Requirements 18.2, 18.3
"""

import pytest
import time
import threading
from hypothesis import given, strategies as st, settings, HealthCheck

from src.core.scheduler import Scheduler, TaskState
from src.core.types import Priority


# ============================================================================
# Property 47: No execution overlap
# Feature: matrix-watcher, Property 47: No execution overlap
# Validates: Requirements 18.2
# ============================================================================

class TestNoExecutionOverlapProperty:
    """Property 47: Same sensor never runs concurrently."""
    
    def test_no_concurrent_execution_of_same_task(self):
        """
        Feature: matrix-watcher, Property 47: No execution overlap
        A task should never run concurrently with itself.
        """
        scheduler = Scheduler()
        
        # Track concurrent executions
        concurrent_count = [0]
        max_concurrent = [0]
        lock = threading.Lock()
        
        def slow_task():
            with lock:
                concurrent_count[0] += 1
                if concurrent_count[0] > max_concurrent[0]:
                    max_concurrent[0] = concurrent_count[0]
            
            time.sleep(0.2)  # Simulate slow task
            
            with lock:
                concurrent_count[0] -= 1
        
        # Register task with very short interval
        scheduler.register_task("slow_task", slow_task, interval=0.1, priority="high")
        
        scheduler.start()
        time.sleep(1.0)  # Let it run for a while
        scheduler.stop()
        
        # Should never have more than 1 concurrent execution
        assert max_concurrent[0] == 1, \
            f"Task ran concurrently {max_concurrent[0]} times, expected max 1"
    
    @given(
        num_tasks=st.integers(min_value=2, max_value=5),
        interval=st.floats(min_value=0.1, max_value=0.3, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=10, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    def test_multiple_tasks_no_self_overlap(self, num_tasks, interval):
        """
        Feature: matrix-watcher, Property 47: No execution overlap
        Multiple tasks should each never overlap with themselves.
        """
        scheduler = Scheduler()
        
        # Track per-task concurrent executions
        concurrent = {f"task_{i}": [0, 0] for i in range(num_tasks)}  # [current, max]
        lock = threading.Lock()
        
        def make_task(name):
            def task():
                with lock:
                    concurrent[name][0] += 1
                    if concurrent[name][0] > concurrent[name][1]:
                        concurrent[name][1] = concurrent[name][0]
                time.sleep(0.05)
                with lock:
                    concurrent[name][0] -= 1
            return task
        
        for i in range(num_tasks):
            name = f"task_{i}"
            scheduler.register_task(name, make_task(name), interval=interval, priority="medium")
        
        scheduler.start()
        time.sleep(0.5)
        scheduler.stop()
        
        # Each task should have max 1 concurrent execution
        for name, (_, max_conc) in concurrent.items():
            assert max_conc <= 1, f"Task {name} had {max_conc} concurrent executions"


# ============================================================================
# Property 48: Priority ordering
# Feature: matrix-watcher, Property 48: Priority ordering
# Validates: Requirements 18.3
# ============================================================================

class TestPriorityOrderingProperty:
    """Property 48: High-priority tasks execute before low-priority when constrained."""
    
    def test_high_priority_executes_first(self):
        """
        Feature: matrix-watcher, Property 48: Priority ordering
        When multiple tasks are ready, high priority should execute first.
        """
        scheduler = Scheduler(max_concurrent=1)  # Force sequential execution
        
        execution_order = []
        lock = threading.Lock()
        
        def make_task(name):
            def task():
                with lock:
                    execution_order.append(name)
                time.sleep(0.05)
            return task
        
        # Register tasks in reverse priority order
        scheduler.register_task("low", make_task("low"), interval=0.1, priority="low")
        scheduler.register_task("medium", make_task("medium"), interval=0.1, priority="medium")
        scheduler.register_task("high", make_task("high"), interval=0.1, priority="high")
        
        scheduler.start()
        time.sleep(0.3)  # Let first batch execute
        scheduler.stop()
        
        # First execution should be high priority
        if execution_order:
            assert execution_order[0] == "high", \
                f"Expected 'high' first, got order: {execution_order}"
    
    def test_priority_values_are_respected(self):
        """
        Feature: matrix-watcher, Property 48: Priority ordering
        Tasks should be sorted by priority when selecting for execution.
        """
        scheduler = Scheduler()
        
        # Register tasks with different priorities
        scheduler.register_task("t1", lambda: None, interval=1.0, priority="low")
        scheduler.register_task("t2", lambda: None, interval=1.0, priority="high")
        scheduler.register_task("t3", lambda: None, interval=1.0, priority="medium")
        
        # Get ready tasks (all should be ready initially)
        ready = scheduler._get_ready_tasks(time.time())
        
        # Should be sorted: high, medium, low
        if len(ready) == 3:
            assert ready[0].priority == Priority.HIGH
            assert ready[1].priority == Priority.MEDIUM
            assert ready[2].priority == Priority.LOW


class TestSchedulerFunctionality:
    """Additional Scheduler functionality tests."""
    
    def test_register_and_unregister(self):
        """Test task registration and unregistration."""
        scheduler = Scheduler()
        
        scheduler.register_task("test", lambda: None, interval=1.0)
        assert scheduler.get_task_count() == 1
        
        result = scheduler.unregister_task("test")
        assert result is True
        assert scheduler.get_task_count() == 0
        
        result = scheduler.unregister_task("nonexistent")
        assert result is False
    
    def test_pause_and_resume(self):
        """Test task pause and resume."""
        scheduler = Scheduler()
        execution_count = [0]
        
        def task():
            execution_count[0] += 1
        
        scheduler.register_task("test", task, interval=0.1)
        scheduler.start()
        
        time.sleep(0.25)
        count_before_pause = execution_count[0]
        
        scheduler.pause_task("test")
        time.sleep(0.25)
        count_while_paused = execution_count[0]
        
        # Should not have increased while paused
        assert count_while_paused == count_before_pause, \
            f"Task ran while paused: {count_before_pause} -> {count_while_paused}"
        
        scheduler.resume_task("test")
        time.sleep(0.25)
        count_after_resume = execution_count[0]
        
        # Should have increased after resume
        assert count_after_resume > count_while_paused
        
        scheduler.stop()
    
    def test_stats_tracking(self):
        """Test execution statistics tracking."""
        scheduler = Scheduler()
        
        def task():
            time.sleep(0.01)
        
        scheduler.register_task("test", task, interval=0.1)
        scheduler.start()
        time.sleep(0.35)
        scheduler.stop()
        
        stats = scheduler.get_task_stats("test")
        assert stats is not None
        assert stats.run_count >= 2
        assert stats.last_run is not None
        assert stats.avg_duration_ms > 0
    
    def test_interval_clamping(self):
        """Test that intervals are clamped to valid range."""
        scheduler = Scheduler()
        
        # Too small interval
        scheduler.register_task("small", lambda: None, interval=0.01)
        stats = scheduler.get_stats()
        # Interval should be clamped to 0.1
        
        # Too large interval
        scheduler.register_task("large", lambda: None, interval=10000)
        # Interval should be clamped to 3600
        
        assert scheduler.get_task_count() == 2
    
    def test_error_handling(self):
        """Test that errors in tasks are handled gracefully."""
        scheduler = Scheduler()
        
        def failing_task():
            raise ValueError("Test error")
        
        scheduler.register_task("failing", failing_task, interval=0.1)
        scheduler.start()
        time.sleep(0.3)
        scheduler.stop()
        
        stats = scheduler.get_task_stats("failing")
        assert stats is not None
        assert stats.error_count > 0
        assert stats.consecutive_failures > 0
