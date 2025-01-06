"""This module imports all commands from the `/commands` directory and loads them into the bot."""
import importlib
import os

def load_commands(client, tree, guild):
    """Imports all the commands in this directory."""
    for filename in os.listdir("./commands"):
        if filename.endswith(".py"):
            module_name = f"commands.{filename[:-3]}"
            module = importlib.import_module(module_name)
            if hasattr(module, 'setup'):
                module.setup(client, tree, guild)  # Pass client and tree to the setup function
