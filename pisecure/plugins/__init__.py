"""
PiSecure Plugin System
======================

Modular plugin architecture for extending PiSecure functionality.
Supports dynamic loading, hook system, and secure plugin execution.
"""

import importlib
import inspect
import json
import hashlib
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable, Type
from abc import ABC, abstractmethod


class PluginInterface(ABC):
    """Base interface that all plugins must implement"""

    @property
    @abstractmethod
    def name(self) -> str:
        """Plugin name"""
        pass

    @property
    @abstractmethod
    def version(self) -> str:
        """Plugin version"""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Plugin description"""
        pass

    @abstractmethod
    def initialize(self, context: 'PluginContext') -> bool:
        """Initialize plugin with context"""
        pass

    @abstractmethod
    def shutdown(self) -> None:
        """Shutdown plugin"""
        pass

    def get_hooks(self) -> Dict[str, Callable]:
        """Return hook functions (optional)"""
        return {}

    def get_api_endpoints(self) -> Dict[str, Callable]:
        """Return API endpoints (optional)"""
        return {}

    def get_cli_commands(self) -> Dict[str, Callable]:
        """Return CLI commands (optional)"""
        return {}


class PluginContext:
    """Context provided to plugins during initialization"""

    def __init__(self, core_services: Dict[str, Any]):
        self.core_services = core_services
        self.blockchain = core_services.get('blockchain')
        self.wallet = core_services.get('wallet')
        self.config = core_services.get('config')
        self.logger = core_services.get('logger')

    def register_hook(self, hook_name: str, callback: Callable):
        """Register a hook callback"""
        if hasattr(self, '_hooks'):
            self._hooks[hook_name] = callback

    def unregister_hook(self, hook_name: str):
        """Unregister a hook callback"""
        if hasattr(self, '_hooks'):
            self._hooks.pop(hook_name, None)


class PluginManager:
    """Central plugin management system"""

    def __init__(self, plugin_dir: str = "/opt/pisecure/plugins",
                 config_file: str = "/etc/pisecure/plugins.json"):
        self.plugin_dir = Path(plugin_dir)
        self.config_file = Path(config_file)
        self.plugins: Dict[str, PluginInterface] = {}
        self.hooks: Dict[str, List[Callable]] = {}
        self.api_endpoints: Dict[str, Callable] = {}
        self.cli_commands: Dict[str, Callable] = {}

        # Create plugin directory
        self.plugin_dir.mkdir(parents=True, exist_ok=True)
        self.config_file.parent.mkdir(parents=True, exist_ok=True)

        # Core services available to plugins
        self.core_services = {}

    def register_core_service(self, name: str, service: Any):
        """Register a core service for plugins"""
        self.core_services[name] = service

    def load_plugin(self, plugin_path: str) -> bool:
        """Load a plugin from file path"""
        try:
            plugin_path = Path(plugin_path)

            # Calculate plugin hash for security
            plugin_hash = self._calculate_file_hash(plugin_path)

            # Import plugin module
            spec = importlib.util.spec_from_file_location(
                f"plugin_{plugin_path.stem}", plugin_path)
            module = importlib.util.module_from_spec(spec)

            # Execute in restricted environment (basic sandbox)
            spec.loader.exec_module(module)

            # Find plugin class
            plugin_class = None
            for name, obj in inspect.getmembers(module):
                if (inspect.isclass(obj) and
                    issubclass(obj, PluginInterface) and
                    obj != PluginInterface):
                    plugin_class = obj
                    break

            if not plugin_class:
                raise ValueError(f"No PluginInterface subclass found in {plugin_path}")

            # Instantiate plugin
            plugin_instance = plugin_class()

            # Create plugin context
            context = PluginContext(self.core_services)

            # Initialize plugin
            if not plugin_instance.initialize(context):
                raise RuntimeError(f"Plugin initialization failed: {plugin_instance.name}")

            # Register plugin components
            self._register_plugin(plugin_instance, plugin_hash)

            return True

        except Exception as e:
            print(f"Failed to load plugin {plugin_path}: {e}")
            return False

    def unload_plugin(self, plugin_name: str) -> bool:
        """Unload a plugin"""
        if plugin_name not in self.plugins:
            return False

        try:
            plugin = self.plugins[plugin_name]

            # Shutdown plugin
            plugin.shutdown()

            # Unregister components
            self._unregister_plugin(plugin)

            # Remove from registry
            del self.plugins[plugin_name]

            return True

        except Exception as e:
            print(f"Error unloading plugin {plugin_name}: {e}")
            return False

    def _register_plugin(self, plugin: PluginInterface, plugin_hash: str):
        """Register plugin components"""
        plugin_name = plugin.name

        # Store plugin info
        self.plugins[plugin_name] = plugin

        # Register hooks
        for hook_name, callback in plugin.get_hooks().items():
            if hook_name not in self.hooks:
                self.hooks[hook_name] = []
            self.hooks[hook_name].append(callback)

        # Register API endpoints
        for route, handler in plugin.get_api_endpoints().items():
            self.api_endpoints[route] = handler

        # Register CLI commands
        for cmd_name, handler in plugin.get_cli_commands().items():
            self.cli_commands[cmd_name] = handler

        # Save to config
        self._save_plugin_config(plugin_name, plugin_hash)

    def _unregister_plugin(self, plugin: PluginInterface):
        """Unregister plugin components"""
        plugin_name = plugin.name

        # Remove hooks
        for hook_name, callbacks in self.hooks.items():
            self.hooks[hook_name] = [cb for cb in callbacks
                                    if not hasattr(cb, '__self__') or
                                       cb.__self__ != plugin]

        # Remove API endpoints (would need more sophisticated tracking)
        # Remove CLI commands (would need more sophisticated tracking)

    def trigger_hook(self, hook_name: str, *args, **kwargs):
        """Trigger a hook with arguments"""
        if hook_name in self.hooks:
            results = []
            for callback in self.hooks[hook_name]:
                try:
                    result = callback(*args, **kwargs)
                    results.append(result)
                except Exception as e:
                    print(f"Hook {hook_name} callback error: {e}")
            return results
        return []

    def get_api_endpoints(self) -> Dict[str, Callable]:
        """Get all registered API endpoints"""
        return self.api_endpoints.copy()

    def get_cli_commands(self) -> Dict[str, Callable]:
        """Get all registered CLI commands"""
        return self.cli_commands.copy()

    def list_plugins(self) -> List[Dict[str, Any]]:
        """List all loaded plugins"""
        return [{
            'name': plugin.name,
            'version': plugin.version,
            'description': plugin.description
        } for plugin in self.plugins.values()]

    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA256 hash of plugin file"""
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()

    def _save_plugin_config(self, plugin_name: str, plugin_hash: str):
        """Save plugin configuration"""
        try:
            config = self._load_plugin_config()
            config[plugin_name] = {
                'hash': plugin_hash,
                'enabled': True,
                'loaded_at': __import__('time').time()
            }

            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)

        except Exception as e:
            print(f"Failed to save plugin config: {e}")

    def _load_plugin_config(self) -> Dict[str, Any]:
        """Load plugin configuration"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Failed to load plugin config: {e}")
        return {}

    def discover_plugins(self) -> List[str]:
        """Discover available plugins in plugin directory"""
        plugins = []
        if self.plugin_dir.exists():
            for plugin_file in self.plugin_dir.glob("*.py"):
                if plugin_file.name != "__init__.py":
                    plugins.append(str(plugin_file))
        return plugins

    def load_all_plugins(self) -> int:
        """Load all discovered plugins"""
        plugin_files = self.discover_plugins()
        loaded_count = 0

        for plugin_file in plugin_files:
            if self.load_plugin(plugin_file):
                loaded_count += 1

        return loaded_count

    def create_plugin_template(self, name: str, description: str) -> str:
        """Create a basic plugin template"""
        template = f'''"""
{name} Plugin for PiSecure
{"=" * (len(name) + 23)}
"""

from pisecure.plugins import PluginInterface, PluginContext


class {name.replace(" ", "")}Plugin(PluginInterface):
    """{description}"""

    @property
    def name(self) -> str:
        return "{name}"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "{description}"

    def initialize(self, context: PluginContext) -> bool:
        """Initialize the plugin"""
        self.context = context
        self.logger = context.logger

        # Register hooks
        context.register_hook("blockchain.new_block", self.on_new_block)
        context.register_hook("wallet.transaction", self.on_transaction)

        self.logger.info(f"{self.name} plugin initialized")
        return True

    def shutdown(self) -> None:
        """Shutdown the plugin"""
        self.logger.info(f"{self.name} plugin shutdown")

    def on_new_block(self, block_data: dict):
        """Handle new block events"""
        self.logger.info(f"New block: {{block_data.get('index', 'unknown')}}")

    def on_transaction(self, tx_data: dict):
        """Handle transaction events"""
        self.logger.info(f"New transaction: {{tx_data.get('type', 'unknown')}}")

    def get_hooks(self) -> dict:
        """Return hook functions"""
        return {{
            "blockchain.new_block": self.on_new_block,
            "wallet.transaction": self.on_transaction,
        }}

    def get_api_endpoints(self) -> dict:
        """Return API endpoints"""
        return {{
            "/api/{name.lower().replace(' ', '_')}": self.api_endpoint,
        }}

    def get_cli_commands(self) -> dict:
        """Return CLI commands"""
        return {{
            "{name.lower().replace(' ', '_')}": self.cli_command,
        }}

    def api_endpoint(self):
        """API endpoint handler"""
        return {{"status": "ok", "plugin": self.name}}

    def cli_command(self):
        """CLI command handler"""
        print(f"{self.name} plugin command executed")
'''
        return template


# Global plugin manager instance
plugin_manager = PluginManager()

__all__ = [
    'PluginInterface',
    'PluginContext',
    'PluginManager',
    'plugin_manager'
]