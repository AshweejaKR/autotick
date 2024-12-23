# -*- coding: utf-8 -*-
"""
Created on Fri Jun 21 21:03:34 2024

@author: ashwe
"""

import sys, os

def get_keys(key_file):
    config_path = 'config/'
    key_file = config_path + key_file
    try:
        if not os.path.isdir(config_path):
            os.mkdir(config_path)
        key_secret = open(key_file, "r").read().split()
    except FileNotFoundError:
        key_secret = []
        key_secret.append(input("Enter API Key\n"))
        key_secret.append(input("Enter API Secret\n"))
        key_secret.append(input("Enter Client ID/Username\n"))
        key_secret.append(input("Enter Password/PIN\n"))
        key_secret.append(input("Enter TOTP String\n"))

        with open(key_file, "w") as f:
            for key in key_secret:
                    f.write(f'{key}\n')
            f.flush()
            f.close()

    return key_secret
