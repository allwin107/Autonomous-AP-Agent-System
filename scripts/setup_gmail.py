import sys
import os
sys.path.append(os.getcwd())
from app.tools.gmail_tool import gmail_tool

def main():
    print("Starting Gmail OAuth flow...")
    print("Please follow the instructions in the browser to authenticate.")
    gmail_tool.authenticate()
    print("Authentication successful. 'token.json' has been created.")

if __name__ == "__main__":
    main()
