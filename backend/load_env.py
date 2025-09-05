#!/usr/bin/env python3
"""
Environment loader utility for Jyotishika backend.
This script helps load environment variables from local.env file.
"""

import os
from pathlib import Path

def load_env_file(env_file_path="local.env"):
    """
    Load environment variables from a .env file.
    
    Args:
        env_file_path (str): Path to the environment file
        
    Returns:
        dict: Dictionary of environment variables
    """
    env_vars = {}
    env_path = Path(env_file_path)
    
    if not env_path.exists():
        print(f"Warning: Environment file {env_file_path} not found")
        return env_vars
    
    with open(env_path, 'r') as f:
        for line in f:
            line = line.strip()
            # Skip empty lines and comments
            if not line or line.startswith('#'):
                continue
            
            # Split on first '=' to handle values with '=' in them
            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
                
                # Remove quotes if present
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                elif value.startswith("'") and value.endswith("'"):
                    value = value[1:-1]
                
                env_vars[key] = value
    
    return env_vars

def set_env_variables(env_file_path="local.env"):
    """
    Set environment variables from a .env file.
    
    Args:
        env_file_path (str): Path to the environment file
    """
    env_vars = load_env_file(env_file_path)
    
    for key, value in env_vars.items():
        if key not in os.environ:  # Don't override existing env vars
            os.environ[key] = value
            print(f"Set {key}={value}")
        else:
            print(f"Skipped {key} (already set)")

if __name__ == "__main__":
    print("Loading environment variables from local.env...")
    set_env_variables()
    print("Environment variables loaded!")
