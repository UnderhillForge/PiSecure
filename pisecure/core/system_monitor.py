"""
PiSecure System Monitor - Track CPU temperature, memory, and system resources
"""

import os
import subprocess
from typing import Dict, Any, Optional


class SystemMonitor:
    """Monitor Raspberry Pi system resources for mining dashboard"""
    
    def __init__(self):
        self.pi_model = self._detect_pi_model()
        
    def _detect_pi_model(self) -> str:
        """Detect Raspberry Pi model"""
        try:
            with open('/proc/device-tree/model', 'r') as f:
                model = f.read().strip('\x00')
                if 'Pi 5' in model:
                    return 'Raspberry Pi 5'
                elif 'Pi 4' in model:
                    return 'Raspberry Pi 4'
                elif 'Pi 3' in model:
                    return 'Raspberry Pi 3'
                elif 'Pi Zero' in model:
                    return 'Raspberry Pi Zero'
                return model
        except:
            # Non-Pi platforms (e.g., macOS) will land here
            return 'Non-Pi Hardware'
    
    def get_cpu_temperature(self) -> float:
        """Get CPU temperature in Celsius"""
        try:
            # Try vcgencmd (official method)
            result = subprocess.run(
                ['vcgencmd', 'measure_temp'],
                capture_output=True,
                text=True,
                timeout=1
            )
            if result.returncode == 0:
                # Output format: temp=45.0'C
                temp_str = result.stdout.strip()
                temp = float(temp_str.replace("temp=", "").replace("'C", ""))
                return temp
        except:
            pass
        
        try:
            # Fallback: thermal zone
            with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                temp = float(f.read().strip()) / 1000.0
                return temp
        except:
            pass
        
        return 0.0  # Unknown
    
    def get_memory_usage(self) -> Dict[str, Any]:
        """Get memory usage statistics"""
        try:
            with open('/proc/meminfo', 'r') as f:
                meminfo = {}
                for line in f:
                    parts = line.split(':')
                    if len(parts) == 2:
                        key = parts[0].strip()
                        value = parts[1].strip().split()[0]
                        meminfo[key] = int(value)
                
                total = meminfo.get('MemTotal', 0)
                available = meminfo.get('MemAvailable', 0)
                used = total - available
                percent = (used / total * 100) if total > 0 else 0
                
                return {
                    'total_mb': total // 1024,
                    'used_mb': used // 1024,
                    'available_mb': available // 1024,
                    'percent': percent
                }
        except:
            return {
                'total_mb': 0,
                'used_mb': 0,
                'available_mb': 0,
                'percent': 0.0
            }
    
    def get_cpu_usage(self) -> float:
        """Get current CPU usage percentage"""
        try:
            # Read /proc/stat for CPU usage
            with open('/proc/stat', 'r') as f:
                line = f.readline()
                if line.startswith('cpu '):
                    parts = line.split()[1:]
                    total = sum(int(x) for x in parts)
                    idle = int(parts[3])
                    # Calculate percentage
                    if hasattr(self, '_last_total'):
                        delta_total = total - self._last_total
                        delta_idle = idle - self._last_idle
                        if delta_total > 0:
                            usage = 100.0 * (1.0 - delta_idle / delta_total)
                        else:
                            usage = 0.0
                    else:
                        usage = 0.0
                    
                    self._last_total = total
                    self._last_idle = idle
                    return usage
        except:
            pass
        
        return 0.0
    
    def get_throttle_status(self) -> str:
        """Get thermal throttling status"""
        temp = self.get_cpu_temperature()
        
        if temp >= 80:
            return "EMERGENCY_STOP"
        elif temp >= 75:
            return "HEAVY_THROTTLE"
        elif temp >= 70:
            return "LIGHT_THROTTLE"
        else:
            return "NORMAL"
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status for dashboard"""
        temp = self.get_cpu_temperature()
        memory = self.get_memory_usage()
        cpu = self.get_cpu_usage()
        throttle = self.get_throttle_status()
        
        return {
            'temperature': temp,
            'memory_percent': memory['percent'],
            'memory_used_mb': memory['used_mb'],
            'memory_total_mb': memory['total_mb'],
            'cpu_percent': cpu,
            'throttle_status': throttle,
            'pi_model': self.pi_model
        }


if __name__ == '__main__':
    """Test system monitor"""
    monitor = SystemMonitor()
    status = monitor.get_system_status()
    print("System Status:")
    print(f"  Pi Model: {status['pi_model']}")
    print(f"  Temperature: {status['temperature']:.1f}°C")
    print(f"  Memory: {status['memory_percent']:.1f}% ({status['memory_used_mb']}MB / {status['memory_total_mb']}MB)")
    print(f"  CPU: {status['cpu_percent']:.1f}%")
    print(f"  Throttle: {status['throttle_status']}")
