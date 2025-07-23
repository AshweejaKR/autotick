#!/usr/bin/env python3
"""
Script to update all exception blocks with function names for better debugging
"""

import re
import os

def update_exception_blocks():
    """Update all exception blocks to include function names"""
    
    # Define the files and their function mappings
    files_to_update = {
        'broker_angleone.py': [
            ('except Exception as err:\n            template = "An exception of type {0} occurred. error message:{1!r}"', 'get_ltp'),
            ('except Exception as err:\n                template = "An exception of type {0} occurred. error message:{1!r}"', 'place_order'),
            ('except Exception as err:\n                    template = "An exception of type {0} occurred. error message:{1!r}"', 'get_order_status'),
            ('except Exception as err:\n            template = "An exception of type {0} occurred. error message:{1!r}"', 'get_available_margin'),
            ('except Exception as err:\n            template = "An exception of type {0} occurred. error message:{1!r}"', 'verify_position'),
            ('except Exception as err:\n            template = "An exception of type {0} occurred. error message:{1!r}"', 'verify_holding'),
            ('except Exception as err:\n            template = "An exception of type {0} occurred. error message:{1!r}"', 'get_entry_exit_price'),
        ],
        'broker_aliceblue.py': [
            ('except Exception as err:\n            template = "An exception of type {0} occurred. error message:{1!r}"', '__login'),
            ('except Exception as err:\n            template = "An exception of type {0} occurred. error message:{1!r}"', '__get_hist_data'),
            ('except Exception as err:\n            template = "An exception of type {0} occurred. error message:{1!r}"', 'get_ltp'),
            ('except Exception as err:\n            template = "An exception of type {0} occurred. error message:{1!r}"', 'place_order'),
            ('except Exception as err:\n            template = "An exception of type {0} occurred. error message:{1!r}"', 'get_order_status'),
            ('except Exception as err:\n            template = "An exception of type {0} occurred. error message:{1!r}"', 'get_available_margin'),
            ('except Exception as err:\n            template = "An exception of type {0} occurred. error message:{1!r}"', 'verify_position'),
            ('except Exception as err:\n            template = "An exception of type {0} occurred. error message:{1!r}"', 'verify_holding'),
            ('except Exception as err:\n            template = "An exception of type {0} occurred. error message:{1!r}"', 'get_entry_exit_price'),
        ]
    }
    
    print("Starting exception block updates with function names...")
    
    # Update each file
    for file_path, function_mappings in files_to_update.items():
        if os.path.exists(file_path):
            print(f"Updating {file_path}...")
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Track which functions we've seen to avoid duplicates
            function_count = {}
            
            # Split content into lines to analyze function context
            lines = content.split('\n')
            current_function = None
            
            # Parse file to identify current function for each exception block
            for i, line in enumerate(lines):
                # Check if this line starts a function definition
                if line.strip().startswith('def '):
                    function_match = re.match(r'\s*def\s+([a-zA-Z_][a-zA-Z0-9_]*)', line)
                    if function_match:
                        current_function = function_match.group(1)
                
                # Check if this line contains an exception block that needs updating
                if 'except Exception as err:' in line and i + 1 < len(lines):
                    next_line = lines[i + 1]
                    if 'template = "An exception of type {0} occurred. error message:{1!r}"' in next_line:
                        if current_function:
                            # Update the template to include function name
                            lines[i + 1] = next_line.replace(
                                'template = "An exception of type {0} occurred. error message:{1!r}"',
                                f'template = "An exception of type {{0}} occurred in function {current_function}(). error message:{{1!r}}"'
                            )
                            print(f"  Updated exception block in function: {current_function}")
            
            # Write updated content back to file
            updated_content = '\n'.join(lines)
            with open(file_path, 'w') as f:
                f.write(updated_content)
            
            print(f"Completed updating {file_path}")
        else:
            print(f"File {file_path} not found, skipping...")
    
    print("All exception block updates completed!")

if __name__ == "__main__":
    update_exception_blocks()
