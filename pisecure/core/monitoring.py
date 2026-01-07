"""
PiSecure System Resource Monitoring and Thermal Management
==========================================================

Comprehensive system monitoring with temperature-based throttling,
memory management, and cool-off strategies for stable mining operations.
"""

import time
import psutil
import os
import gc
import threading
import subprocess
import re
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum


class ThrottleLevel(Enum):
    """Mining throttle levels based on system conditions"""
    NORMAL = "normal"
    LIGHT_THROTTLE = "light_throttle"
    HEAVY_THROTTLE = "heavy_throttle"
    PAUSED = "paused"
    EMERGENCY_STOP = "emergency_stop"


@dataclass
class SystemResources:
    """System resource snapshot"""
    temperature: float
    cpu_percent: float
    memory_percent: float
    memory_used_gb: float
    memory_available_gb: float
    load_average: tuple
    disk_usage_percent: float
    mining_process_memory_mb: float
    timestamp: float


class SystemResourceMonitor:
    """
    Comprehensive system resource monitoring for mining operations

    Monitors temperature, memory, CPU, and provides throttling recommendations
    to prevent system crashes during extended mining sessions.
    """

    def __init__(self):
        # Temperature thresholds (Pi 5 specific - higher than Pi 4)
        self.temperature_thresholds = {
            'warning': 70.0,    # Start light throttling
            'critical': 75.0,   # Pause mining temporarily
            'emergency': 80.0   # Stop mining completely
        }

        # Memory thresholds
        self.memory_thresholds = {
            'warning': 80.0,    # Start memory cleanup
            'critical': 90.0,   # Aggressive cleanup
            'emergency': 95.0   # Emergency stop
        }

        # CPU thresholds
        self.cpu_thresholds = {
            'warning': 85.0,    # High CPU usage
            'critical': 95.0,   # Very high CPU usage
        }

        # Load average thresholds (1-minute average)
        self.load_thresholds = {
            'warning': 2.0,     # High load
            'critical': 4.0,    # Very high load
        }

        # Throttling configuration
        self.throttle_delays = {
            ThrottleLevel.NORMAL: 2.0,           # Normal 2-second delay
            ThrottleLevel.LIGHT_THROTTLE: 5.0,   # 5-second delay when warm
            ThrottleLevel.HEAVY_THROTTLE: 15.0,  # 15-second delay when hot
            ThrottleLevel.PAUSED: 60.0,          # 1-minute pause when critical
        }

        # Memory management
        self.last_gc_time = 0
        self.gc_interval = 30  # Force GC every 30 seconds

        # Monitoring state
        self.monitoring_active = False
        self.monitoring_thread: Optional[threading.Thread] = None
        self.last_resources: Optional[SystemResources] = None
        self.throttle_level = ThrottleLevel.NORMAL
        self.cool_down_until = 0

    def start_monitoring(self):
        """Start background system monitoring"""
        if self.monitoring_active:
            return

        self.monitoring_active = True
        self.monitoring_thread = threading.Thread(
            target=self._monitoring_loop,
            daemon=True,
            name="SystemMonitor"
        )
        self.monitoring_thread.start()

    def stop_monitoring(self):
        """Stop background monitoring"""
        self.monitoring_active = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=2.0)

    def check_system_resources(self) -> Dict[str, Any]:
        """
        Comprehensive system resource check

        Returns detailed system status and throttling recommendations
        """
        try:
            # Get current resources
            resources = self._get_current_resources()

            # Analyze system health
            health_analysis = self._analyze_system_health(resources)

            # Determine throttle level
            throttle_recommendation = self._calculate_throttle_level(resources)

            # Memory management
            memory_status = self._check_memory_status(resources)

            return {
                'resources': resources,
                'health': health_analysis,
                'throttle_level': throttle_recommendation,
                'memory_status': memory_status,
                'should_pause_mining': self._should_pause_mining(resources),
                'recommended_delay': self._get_recommended_delay(throttle_recommendation),
                'cool_down_time_remaining': max(0, self.cool_down_until - time.time())
            }

        except Exception as e:
            # Return safe defaults on error
            return {
                'resources': None,
                'health': {'status': 'error', 'message': str(e)},
                'throttle_level': ThrottleLevel.EMERGENCY_STOP,
                'memory_status': {'needs_cleanup': True},
                'should_pause_mining': True,
                'recommended_delay': 60.0,
                'cool_down_time_remaining': 0
            }

    def _get_current_resources(self) -> SystemResources:
        """Get current system resource snapshot"""
        # CPU temperature (try multiple methods)
        temperature = self._get_cpu_temperature()

        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=0.1)

        # Memory usage
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        memory_used_gb = memory.used / (1024**3)
        memory_available_gb = memory.available / (1024**3)

        # System load
        load_average = os.getloadavg()

        # Disk usage (root filesystem)
        disk = psutil.disk_usage('/')
        disk_usage_percent = disk.percent

        # Mining process memory (approximate)
        mining_memory_mb = self._get_mining_process_memory()

        return SystemResources(
            temperature=temperature,
            cpu_percent=cpu_percent,
            memory_percent=memory_percent,
            memory_used_gb=memory_used_gb,
            memory_available_gb=memory_available_gb,
            load_average=load_average,
            disk_usage_percent=disk_usage_percent,
            mining_process_memory_mb=mining_memory_mb,
            timestamp=time.time()
        )

    def _get_cpu_temperature(self) -> float:
        """Get CPU temperature using multiple fallback methods"""
        # Method 1: vcgencmd (most reliable for Pi)
        try:
            result = subprocess.run(['vcgencmd', 'measure_temp'],
                                  capture_output=True, text=True, timeout=2)
            if result.returncode == 0:
                temp_match = re.search(r'temp=([0-9.]+)', result.stdout)
                if temp_match:
                    return float(temp_match.group(1))
        except:
            pass

        # Method 2: Thermal zones
        try:
            with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                temp_raw = int(f.read().strip())
                return temp_raw / 1000.0  # Convert to Celsius
        except:
            pass

        # Ultimate fallback
        return 50.0  # Safe default

    def _get_mining_process_memory(self) -> float:
        """Get memory usage of mining-related processes"""
        try:
            current_process = psutil.Process()
            # Include child processes
            total_memory = current_process.memory_info().rss

            for child in current_process.children(recursive=True):
                try:
                    total_memory += child.memory_info().rss
                except:
                    pass

            return total_memory / (1024**2)  # Convert to MB
        except:
            return 0.0

    def _analyze_system_health(self, resources: SystemResources) -> Dict[str, Any]:
        """Analyze overall system health"""
        issues = []
        warnings = []

        # Temperature analysis
        if resources.temperature >= self.temperature_thresholds['emergency']:
            issues.append(f"EMERGENCY: Temperature {resources.temperature:.1f}C")
        elif resources.temperature >= self.temperature_thresholds['critical']:
            issues.append(f"CRITICAL: Temperature {resources.temperature:.1f}C")
        elif resources.temperature >= self.temperature_thresholds['warning']:
            warnings.append(f"WARNING: High temperature {resources.temperature:.1f}C")

        # Memory analysis
        if resources.memory_percent >= self.memory_thresholds['emergency']:
            issues.append(f"EMERGENCY: Memory usage {resources.memory_percent:.1f}%")
        elif resources.memory_percent >= self.memory_thresholds['critical']:
            issues.append(f"CRITICAL: Memory usage {resources.memory_percent:.1f}%")
        elif resources.memory_percent >= self.memory_thresholds['warning']:
            warnings.append(f"WARNING: High memory usage {resources.memory_percent:.1f}%")

        # CPU analysis
        if resources.cpu_percent >= self.cpu_thresholds['critical']:
            issues.append(f"CRITICAL: CPU usage {resources.cpu_percent:.1f}%")
        elif resources.cpu_percent >= self.cpu_thresholds['warning']:
            warnings.append(f"WARNING: High CPU usage {resources.cpu_percent:.1f}%")

        # Load analysis
        if resources.load_average[0] >= self.load_thresholds['critical']:
            issues.append(f"CRITICAL: System load {resources.load_average[0]:.1f}")
        elif resources.load_average[0] >= self.load_thresholds['warning']:
            warnings.append(f"WARNING: High system load {resources.load_average[0]:.1f}")

        # Overall status
        if issues:
            status = 'critical'
            message = " | ".join(issues)
        elif warnings:
            status = 'warning'
            message = " | ".join(warnings)
        else:
            status = 'healthy'
            message = "All systems normal"

        return {
            'status': status,
            'message': message,
            'issues': issues,
            'warnings': warnings,
            'temperature_status': self._classify_temperature(resources.temperature),
            'memory_status': self._classify_resource(resources.memory_percent, self.memory_thresholds),
            'cpu_status': self._classify_resource(resources.cpu_percent, self.cpu_thresholds),
            'load_status': self._classify_resource(resources.load_average[0], self.load_thresholds)
        }

    def _classify_temperature(self, temp: float) -> str:
        """Classify temperature status"""
        if temp >= self.temperature_thresholds['emergency']:
            return 'emergency'
        elif temp >= self.temperature_thresholds['critical']:
            return 'critical'
        elif temp >= self.temperature_thresholds['warning']:
            return 'warning'
        else:
            return 'normal'

    def _classify_resource(self, value: float, thresholds: Dict[str, float]) -> str:
        """Classify resource usage status"""
        if value >= thresholds.get('emergency', 100):
            return 'emergency'
        elif value >= thresholds.get('critical', 100):
            return 'critical'
        elif value >= thresholds.get('warning', 100):
            return 'warning'
        else:
            return 'normal'

    def _calculate_throttle_level(self, resources: SystemResources) -> ThrottleLevel:
        """Calculate appropriate throttle level based on system resources"""
        # Emergency conditions
        if (resources.temperature >= self.temperature_thresholds['emergency'] or
            resources.memory_percent >= self.memory_thresholds['emergency'] or
            resources.cpu_percent >= self.cpu_thresholds['critical']):
            return ThrottleLevel.EMERGENCY_STOP

        # Critical conditions
        if (resources.temperature >= self.temperature_thresholds['critical'] or
            resources.memory_percent >= self.memory_thresholds['critical'] or
            resources.load_average[0] >= self.load_thresholds['critical']):
            return ThrottleLevel.PAUSED

        # Heavy throttling
        if (resources.temperature >= self.temperature_thresholds['warning'] or
            resources.memory_percent >= self.memory_thresholds['warning'] or
            resources.cpu_percent >= self.cpu_thresholds['warning']):
            return ThrottleLevel.HEAVY_THROTTLE

        # Light throttling for mild issues
        if resources.load_average[0] >= self.load_thresholds['warning']:
            return ThrottleLevel.LIGHT_THROTTLE

        return ThrottleLevel.NORMAL

    def _should_pause_mining(self, resources: SystemResources) -> bool:
        """Determine if mining should be paused"""
        return (resources.temperature >= self.temperature_thresholds['critical'] or
                resources.memory_percent >= self.memory_thresholds['critical'] or
                time.time() < self.cool_down_until)

    def _get_recommended_delay(self, throttle_level: ThrottleLevel) -> float:
        """Get recommended delay based on throttle level"""
        if throttle_level == ThrottleLevel.EMERGENCY_STOP:
            return 300.0  # 5 minutes
        elif throttle_level == ThrottleLevel.PAUSED:
            return 60.0   # 1 minute
        else:
            return self.throttle_delays.get(throttle_level, 2.0)

    def _check_memory_status(self, resources: SystemResources) -> Dict[str, Any]:
        """Check memory usage and cleanup needs"""
        needs_cleanup = False
        cleanup_priority = 'none'

        # Determine cleanup needs
        if resources.memory_percent >= self.memory_thresholds['emergency']:
            needs_cleanup = True
            cleanup_priority = 'emergency'
        elif resources.memory_percent >= self.memory_thresholds['critical']:
            needs_cleanup = True
            cleanup_priority = 'critical'
        elif resources.memory_percent >= self.memory_thresholds['warning']:
            needs_cleanup = True
            cleanup_priority = 'warning'

        return {
            'needs_cleanup': needs_cleanup,
            'cleanup_priority': cleanup_priority,
            'current_mb': resources.mining_process_memory_mb,
            'available_gb': resources.memory_available_gb
        }

    def perform_memory_cleanup(self, priority: str = 'normal') -> Dict[str, Any]:
        """
        Perform memory cleanup operations

        Args:
            priority: 'normal', 'warning', 'critical', 'emergency'
        """
        cleanup_results = {
            'gc_collections': 0,
            'memory_freed_mb': 0,
            'objects_collected': 0,
            'duration': 0
        }

        start_time = time.time()
        start_memory = self._get_mining_process_memory()

        try:
            # Force garbage collection
            collected = gc.collect()
            cleanup_results['gc_collections'] = 1
            cleanup_results['objects_collected'] = collected

            # Additional cleanup based on priority
            if priority in ['critical', 'emergency']:
                # Clear any caches we can find
                self._clear_system_caches()

                # Force another GC cycle
                collected2 = gc.collect()
                cleanup_results['gc_collections'] = 2
                cleanup_results['objects_collected'] += collected2

            if priority == 'emergency':
                # Most aggressive cleanup
                gc.set_threshold(100, 10, 10)  # Lower GC thresholds temporarily
                collected3 = gc.collect()
                cleanup_results['gc_collections'] = 3
                cleanup_results['objects_collected'] += collected3

        except Exception as e:
            cleanup_results['error'] = str(e)

        # Measure memory freed
        end_memory = self._get_mining_process_memory()
        cleanup_results['memory_freed_mb'] = max(0, start_memory - end_memory)
        cleanup_results['duration'] = time.time() - start_time

        return cleanup_results

    def _clear_system_caches(self):
        """Clear various system caches that might be accumulating"""
        try:
            # Clear Python caches (safe)
            import sys
            if hasattr(sys, '_clear_type_cache'):
                sys._clear_type_cache()

            # Clear DNS cache if available
            import socket
            if hasattr(socket, '_intenum_cache'):
                socket._intenum_cache.clear()

        except:
            pass  # Ignore errors in cache clearing

    def apply_cool_off_strategy(self, system_status: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply cool-off strategy based on system status

        Returns information about the cool-off action taken
        """
        throttle_level = system_status['throttle_level']
        resources = system_status['resources']

        if throttle_level == ThrottleLevel.EMERGENCY_STOP:
            # Emergency stop
            cool_down_duration = 300  # 5 minutes
            self.cool_down_until = time.time() + cool_down_duration

            # Perform emergency memory cleanup
            cleanup_result = self.perform_memory_cleanup('emergency')

            return {
                'action': 'emergency_stop',
                'cool_down_duration': cool_down_duration,
                'memory_cleanup': cleanup_result,
                'reason': f"Temperature {resources.temperature:.1f}C, Memory {resources.memory_percent:.1f}%"
            }

        elif throttle_level == ThrottleLevel.PAUSED:
            # Temporary pause
            cool_down_duration = 60  # 1 minute
            self.cool_down_until = time.time() + cool_down_duration

            # Perform critical memory cleanup
            cleanup_result = self.perform_memory_cleanup('critical')

            return {
                'action': 'pause_mining',
                'cool_down_duration': cool_down_duration,
                'memory_cleanup': cleanup_result,
                'reason': f"High temperature/memory usage"
            }

        elif throttle_level in [ThrottleLevel.HEAVY_THROTTLE, ThrottleLevel.LIGHT_THROTTLE]:
            # Just increase delays and light cleanup
            cleanup_result = self.perform_memory_cleanup('warning')

            return {
                'action': 'throttle_mining',
                'cool_down_duration': 0,
                'memory_cleanup': cleanup_result,
                'reason': f"Increased delays for cooling"
            }

        else:
            # Normal operation - just periodic cleanup
            current_time = time.time()
            if current_time - self.last_gc_time > self.gc_interval:
                cleanup_result = self.perform_memory_cleanup('normal')
                self.last_gc_time = current_time

                return {
                    'action': 'periodic_cleanup',
                    'cool_down_duration': 0,
                    'memory_cleanup': cleanup_result,
                    'reason': 'Periodic maintenance'
                }

        return {'action': 'none', 'reason': 'System normal'}

    def _monitoring_loop(self):
        """Background monitoring loop"""
        while self.monitoring_active:
            try:
                # Update current resources
                self.last_resources = self._get_current_resources()

                # Periodic memory cleanup
                current_time = time.time()
                if current_time - self.last_gc_time > self.gc_interval:
                    self.perform_memory_cleanup('normal')
                    self.last_gc_time = current_time

                # Sleep before next check
                time.sleep(10)  # Check every 10 seconds

            except Exception as e:
                # Log error but continue monitoring
                print(f"Monitoring error: {e}")
                time.sleep(30)  # Longer sleep on error

    def get_monitoring_stats(self) -> Dict[str, Any]:
        """Get monitoring statistics"""
        session_duration = time.time() - time.time()  # Will be set when monitoring starts

        return {
            'monitoring_active': self.monitoring_active,
            'session_duration_hours': session_duration / 3600,
            'current_throttle_level': self.throttle_level.value,
            'cool_down_active': time.time() < self.cool_down_until,
            'last_resources': self.last_resources.__dict__ if self.last_resources else None
        }

    def get_status_display(self, system_status: Dict[str, Any]) -> str:
        """Get human-readable status display for mining output"""
        resources = system_status['resources']

        if not resources:
            return "TEMP N/A | MEM N/A | ERR Monitoring error"

        # Temperature with simple indicators
        temp = resources.temperature
        if temp >= self.temperature_thresholds['emergency']:
            temp_display = f"HOT {temp:.0f}C"
        elif temp >= self.temperature_thresholds['critical']:
            temp_display = f"WARM {temp:.0f}C"
        elif temp >= self.temperature_thresholds['warning']:
            temp_display = f"OK {temp:.0f}C"
        else:
            temp_display = f"COOL {temp:.0f}C"

        # Memory with simple indicators
        mem_pct = resources.memory_percent
        if mem_pct >= self.memory_thresholds['emergency']:
            mem_display = f"HIGH {mem_pct:.0f}%"
        elif mem_pct >= self.memory_thresholds['critical']:
            mem_display = f"MED {mem_pct:.0f}%"
        elif mem_pct >= self.memory_thresholds['warning']:
            mem_display = f"OK {mem_pct:.0f}%"
        else:
            mem_display = f"LOW {mem_pct:.0f}%"

        # Throttle status
        throttle = system_status['throttle_level']
        if throttle == ThrottleLevel.EMERGENCY_STOP:
            status_icon = "STOP"
        elif throttle == ThrottleLevel.PAUSED:
            status_icon = "PAUSE"
        elif throttle == ThrottleLevel.HEAVY_THROTTLE:
            status_icon = "SLOW"
        elif throttle == ThrottleLevel.LIGHT_THROTTLE:
            status_icon = "TURTLE"
        else:
            status_icon = "FAST"

        return f"{temp_display} | {mem_display} | {status_icon}"


# Global monitor instance
system_monitor = SystemResourceMonitor()


def get_system_monitor() -> SystemResourceMonitor:
    """Get global system monitor instance"""
    return system_monitor


def check_mining_safety() -> Dict[str, Any]:
    """Quick safety check for mining operations"""
    return system_monitor.check_system_resources()


def perform_memory_maintenance():
    """Perform routine memory maintenance"""
    system_monitor.perform_memory_cleanup('normal')


# Convenience functions for mining integration
def get_mining_throttle_status() -> Dict[str, Any]:
    """Get current mining throttle status"""
    status = system_monitor.check_system_resources()
    return {
        'can_mine': not status['should_pause_mining'],
        'recommended_delay': status['recommended_delay'],
        'throttle_level': status['throttle_level'].value,
        'status_display': system_monitor.get_status_display(status)
    }
