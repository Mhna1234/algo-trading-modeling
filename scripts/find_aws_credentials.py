"""
AWS Credentials Finder & Extractor
This script helps you locate and verify your AWS credentials.
"""

import os
from pathlib import Path
import json

def check_environment_variables():
    """Check if AWS credentials are set as environment variables."""
    print("=" * 70)
    print("1. CHECKING ENVIRONMENT VARIABLES")
    print("=" * 70)
    
    access_key = os.environ.get('AWS_ACCESS_KEY_ID')
    secret_key = os.environ.get('AWS_SECRET_ACCESS_KEY')
    region = os.environ.get('AWS_DEFAULT_REGION')
    
    if access_key or secret_key:
        print("\n✓ Found AWS credentials in environment variables:")
        if access_key:
            print(f"  AWS_ACCESS_KEY_ID: {access_key[:8]}{'*' * 12} (masked)")
        else:
            print("  AWS_ACCESS_KEY_ID: Not set")
            
        if secret_key:
            print(f"  AWS_SECRET_ACCESS_KEY: {'*' * 40} (hidden)")
        else:
            print("  AWS_SECRET_ACCESS_KEY: Not set")
            
        if region:
            print(f"  AWS_DEFAULT_REGION: {region}")
        else:
            print("  AWS_DEFAULT_REGION: Not set")
        return True
    else:
        print("\n✗ No AWS credentials found in environment variables")
        return False


def check_aws_credentials_file():
    """Check the AWS credentials file."""
    print("\n" + "=" * 70)
    print("2. CHECKING AWS CREDENTIALS FILE")
    print("=" * 70)
    
    creds_path = Path.home() / '.aws' / 'credentials'
    config_path = Path.home() / '.aws' / 'config'
    
    print(f"\nLooking for credentials file at: {creds_path}")
    
    if creds_path.exists():
        print("✓ Credentials file found!")
        print("\nProfiles found:")
        
        try:
            with open(creds_path, 'r') as f:
                content = f.read()
                
            profiles = []
            for line in content.split('\n'):
                line = line.strip()
                if line.startswith('[') and line.endswith(']'):
                    profile = line[1:-1]
                    profiles.append(profile)
                    print(f"  - {profile}")
            
            print("\n" + "-" * 70)
            print("File content (with masked secrets):")
            print("-" * 70)
            
            for line in content.split('\n'):
                if 'aws_secret_access_key' in line.lower():
                    parts = line.split('=', 1)
                    if len(parts) == 2:
                        print(f"{parts[0]}= {'*' * 40} (hidden)")
                    else:
                        print(line)
                else:
                    print(line)
                    
            return True
            
        except Exception as e:
            print(f"✗ Error reading file: {e}")
            return False
    else:
        print(f"✗ Credentials file not found at: {creds_path}")
        
    # Check config file
    print(f"\nLooking for config file at: {config_path}")
    if config_path.exists():
        print("✓ Config file found!")
        try:
            with open(config_path, 'r') as f:
                print("\nConfig file content:")
                print("-" * 70)
                print(f.read())
        except Exception as e:
            print(f"Error reading config: {e}")
    else:
        print(f"✗ Config file not found")
    
    return False


def check_aws_cli_installation():
    """Check if AWS CLI is installed."""
    print("\n" + "=" * 70)
    print("3. CHECKING AWS CLI INSTALLATION")
    print("=" * 70)
    
    import subprocess
    
    try:
        result = subprocess.run(['aws', '--version'], 
                              capture_output=True, 
                              text=True, 
                              timeout=5)
        print(f"✓ AWS CLI installed: {result.stdout.strip()}")
        
        # Try to get caller identity if credentials exist
        print("\nTrying to verify credentials with AWS...")
        try:
            result = subprocess.run(['aws', 'sts', 'get-caller-identity'], 
                                  capture_output=True, 
                                  text=True, 
                                  timeout=10)
            if result.returncode == 0:
                print("✓ AWS credentials are working!")
                identity = json.loads(result.stdout)
                print(f"  Account: {identity.get('Account')}")
                print(f"  User ARN: {identity.get('Arn')}")
                print(f"  User ID: {identity.get('UserId')}")
                return True
            else:
                print(f"✗ Credentials not configured or invalid")
                print(f"  Error: {result.stderr}")
        except Exception as e:
            print(f"✗ Could not verify credentials: {e}")
            
    except FileNotFoundError:
        print("✗ AWS CLI not installed")
        print("\nDownload from: https://aws.amazon.com/cli/")
    except Exception as e:
        print(f"✗ Error checking AWS CLI: {e}")
    
    return False


def provide_instructions():
    """Provide instructions for finding AWS credentials."""
    print("\n" + "=" * 70)
    print("HOW TO FIND YOUR AWS CREDENTIALS")
    print("=" * 70)
    
    print("""
AWS credentials consist of:
  1. Access Key ID (looks like: AKIAIOSFODNN7EXAMPLE)
  2. Secret Access Key (looks like: wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY)

WHERE TO FIND THEM:

Option 1: AWS Console (Web)
--------------------------
1. Log into AWS Console: https://console.aws.amazon.com/
2. Click your name (top right) → Security credentials
3. Scroll to "Access keys" section
4. If you see existing keys:
   - You'll see the Access Key ID
   - Secret key was shown ONLY when created (can't be retrieved)
   - If lost, create a new key pair
5. To create NEW keys:
   - Click "Create access key"
   - Download the CSV or copy both values
   - Store them safely!

Option 2: AWS IAM Console
-------------------------
1. Go to: https://console.aws.amazon.com/iam/
2. Navigate to: Users → [Your Username]
3. Go to "Security credentials" tab
4. Under "Access keys" - same as Option 1

Option 3: Check Email
--------------------
- If someone else created your account, check your email
- AWS sends credentials when accounts are created
- Search for "AWS" or "Access Key"

Option 4: Ask AWS Administrator
-------------------------------
- If you're part of an organization
- Contact your AWS administrator
- They can create new credentials for you

IMPORTANT SECURITY NOTES:
------------------------
• Never share your Secret Access Key
• Don't commit keys to Git/GitHub
• If compromised, delete and create new keys
• Use .env file locally (already in .gitignore)
• Consider using AWS IAM roles instead of keys when possible

""")


def create_env_file_interactive():
    """Guide user to create .env file."""
    print("=" * 70)
    print("CREATE .env FILE")
    print("=" * 70)
    
    print("""
Once you have your AWS credentials, create a .env file:

1. Copy the example file:
   Copy-Item .env.example .env

2. Edit the file:
   notepad .env

3. Replace with your actual credentials:
   AWS_ACCESS_KEY_ID=AKIA................
   AWS_SECRET_ACCESS_KEY=................................
   AWS_DEFAULT_REGION=us-east-1

4. Save and close

5. Test with:
   python scripts/test_s3_setup.py

""")


def main():
    """Main function to run all checks."""
    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 20 + "AWS CREDENTIALS FINDER" + " " * 25 + "║")
    print("╚" + "=" * 68 + "╝")
    print()
    
    found_any = False
    
    # Check environment variables
    if check_environment_variables():
        found_any = True
    
    # Check credentials file
    if check_aws_credentials_file():
        found_any = True
    
    # Check AWS CLI
    if check_aws_cli_installation():
        found_any = True
    
    # Provide instructions
    provide_instructions()
    
    # Guide to create .env
    create_env_file_interactive()
    
    if found_any:
        print("\n" + "=" * 70)
        print("✓ CREDENTIALS FOUND!")
        print("=" * 70)
        print("\nYour AWS credentials are already configured.")
        print("You can now run: python scripts/test_s3_setup.py")
    else:
        print("\n" + "=" * 70)
        print("⚠ NO CREDENTIALS FOUND")
        print("=" * 70)
        print("\nFollow the instructions above to locate your AWS credentials.")
        print("Then create a .env file with your credentials.")
    
    print("\n")


if __name__ == "__main__":
    main()
