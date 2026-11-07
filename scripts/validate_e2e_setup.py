#!/usr/bin/env python3
"""
Integration Test Setup Validator

This script validates that the end-to-end integration test environment is properly configured
and all dependencies are available. It performs comprehensive checks without running the
actual tests, making it safe to use in CI/CD pipelines and development environments.

USAGE:
    python scripts/validate_e2e_setup.py

CHECKS PERFORMED:
- Python package imports
- AWS credentials and service access
- S3 bucket accessibility
- Lambda function availability (optional)
- Test data file existence
- Configuration validation

WHY THIS SCRIPT:
- Quick validation without running expensive tests
- Provides clear error messages for setup issues
- Safe to run in any environment
- Helps diagnose integration test failures
"""

import sys
import os
import boto3
import json
from pathlib import Path
from typing import Dict, List, Tuple

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def check_python_packages() -> Tuple[bool, List[str]]:
    """Check that all required Python packages are available."""
    required_packages = [
        ('pytest', 'pytest'),
        ('boto3', 'boto3'),
        ('botocore', 'botocore'),  
        ('moto', 'moto'),
        ('requests', 'requests'),
        ('faker', 'faker'),
    ]
    
    missing_packages = []
    
    for package_name, import_name in required_packages:
        try:
            __import__(import_name)
        except ImportError:
            missing_packages.append(package_name)
    
    return len(missing_packages) == 0, missing_packages

def check_aws_credentials() -> Tuple[bool, str]:
    """Check AWS credentials and basic connectivity."""
    try:
        session = boto3.Session()
        credentials = session.get_credentials()
        
        if not credentials:
            return False, "No AWS credentials found"
        
        # Test basic AWS access
        sts = boto3.client('sts')
        identity = sts.get_caller_identity()
        
        return True, f"AWS access confirmed for account {identity['Account']}"
        
    except Exception as e:
        return False, f"AWS credentials error: {e}"

def check_s3_access(bucket_name: str) -> Tuple[bool, str]:
    """Check S3 service access and bucket availability."""
    try:
        s3_client = boto3.client('s3')
        
        # Test S3 service access
        s3_client.list_buckets()
        
        # Test specific bucket access
        try:
            s3_client.head_bucket(Bucket=bucket_name)
            return True, f"S3 bucket '{bucket_name}' is accessible"
        except Exception as e:
            return False, f"S3 bucket '{bucket_name}' not accessible: {e}"
            
    except Exception as e:
        return False, f"S3 service access error: {e}"

def check_lambda_function(function_name: str) -> Tuple[bool, str]:
    """Check Lambda function availability (optional)."""
    try:
        lambda_client = boto3.client('lambda')
        response = lambda_client.get_function(FunctionName=function_name)
        
        state = response['Configuration']['State']
        return True, f"Lambda function '{function_name}' is available (State: {state})"
        
    except Exception as e:
        return False, f"Lambda function '{function_name}' not accessible: {e}"

def check_test_files() -> Tuple[bool, List[str]]:
    """Check that test data files exist."""
    required_files = [
        'tests/integration/test_end_to_end.py',
        'scripts/run_e2e_tests.py',
        'pytest-e2e.ini',
        'requirements-test.txt',
        'test_data/transcripts/work/complex_work_transcript.txt',
        'test_data/transcripts/memories/personal_memory_transcript.txt',
        'test_data/transcripts/github_ideas/innovative_project_idea.txt',
        'test_data/transcripts/general/multi_domain_transcript.txt',
    ]
    
    missing_files = []
    
    for file_path in required_files:
        full_path = project_root / file_path
        if not full_path.exists():
            missing_files.append(file_path)
    
    return len(missing_files) == 0, missing_files

def check_test_imports() -> Tuple[bool, str]:
    """Check that test modules can be imported."""
    try:
        from tests.integration.test_end_to_end import WhisperSyncE2ETest, TestEndToEndIntegration
        
        # Test basic instantiation
        test_instance = WhisperSyncE2ETest()
        
        return True, "Test modules import successfully"
        
    except Exception as e:
        return False, f"Test import error: {e}"

def check_configuration() -> Tuple[bool, Dict[str, str]]:
    """Check environment configuration."""
    config = {
        'TEST_BUCKET_NAME': os.environ.get('TEST_BUCKET_NAME', 'macbook-transcriptions-test'),
        'TEST_LAMBDA_FUNCTION_NAME': os.environ.get('TEST_LAMBDA_FUNCTION_NAME', 'whispersync-router'),
        'AWS_DEFAULT_REGION': os.environ.get('AWS_DEFAULT_REGION', 'us-east-1'),
        'TRANSCRIPT_BUCKET_NAME': os.environ.get('TRANSCRIPT_BUCKET_NAME', 'macbook-transcriptions-test'),
    }
    
    return True, config

def main():
    """Main validation function."""
    print("🔍 WhisperSync E2E Integration Test Setup Validator")
    print("=" * 60)
    
    all_checks_passed = True
    
    # Check Python packages
    print("\n📦 Checking Python packages...")
    packages_ok, missing_packages = check_python_packages()
    if packages_ok:
        print("✓ All required Python packages are available")
    else:
        print(f"✗ Missing Python packages: {', '.join(missing_packages)}")
        print("  Install with: pip install -r requirements-test.txt")
        all_checks_passed = False
    
    # Check test imports
    print("\n🐍 Checking test module imports...")
    imports_ok, import_message = check_test_imports()
    if imports_ok:
        print(f"✓ {import_message}")
    else:
        print(f"✗ {import_message}")
        all_checks_passed = False
    
    # Check configuration
    print("\n⚙️ Checking configuration...")
    config_ok, config = check_configuration()
    print("✓ Configuration values:")
    for key, value in config.items():
        print(f"    {key}: {value}")
    
    # Check AWS credentials
    print("\n🔑 Checking AWS credentials...")
    creds_ok, creds_message = check_aws_credentials()
    if creds_ok:
        print(f"✓ {creds_message}")
    else:
        print(f"✗ {creds_message}")
        print("  Configure with: aws configure")
        all_checks_passed = False
    
    # Check S3 access
    if creds_ok:
        print("\n🪣 Checking S3 access...")
        bucket_name = config['TEST_BUCKET_NAME']
        s3_ok, s3_message = check_s3_access(bucket_name)
        if s3_ok:
            print(f"✓ {s3_message}")
        else:
            print(f"✗ {s3_message}")
            print(f"  Create bucket with: aws s3 mb s3://{bucket_name}")
            all_checks_passed = False
    
    # Check Lambda function (optional)
    if creds_ok:
        print("\n⚡ Checking Lambda function...")
        lambda_name = config['TEST_LAMBDA_FUNCTION_NAME']
        lambda_ok, lambda_message = check_lambda_function(lambda_name)
        if lambda_ok:
            print(f"✓ {lambda_message}")
        else:
            print(f"⚠ {lambda_message}")
            print("  Note: Lambda function is optional for basic testing")
    
    # Check test files
    print("\n📁 Checking test files...")
    files_ok, missing_files = check_test_files()
    if files_ok:
        print("✓ All test files are present")
    else:
        print(f"✗ Missing test files:")
        for file_path in missing_files:
            print(f"    {file_path}")
        all_checks_passed = False
    
    # Summary
    print("\n" + "=" * 60)
    if all_checks_passed:
        print("🎉 SUCCESS: All validation checks passed!")
        print("\nYou can now run integration tests:")
        print("  python scripts/run_e2e_tests.py --dry-run")
        print("  python scripts/run_e2e_tests.py")
        return 0
    else:
        print("❌ FAILED: Some validation checks failed")
        print("\nPlease fix the issues above before running integration tests.")
        print("\nFor help, see: tests/integration/README.md")
        return 1

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\nValidation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nUnexpected error during validation: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)