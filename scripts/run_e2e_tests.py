#!/usr/bin/env python3
"""
End-to-End Test Runner for WhisperSync

This script provides a comprehensive test runner for WhisperSync integration tests.
It handles environment validation, AWS service checks, and test execution with
proper reporting and cleanup.

USAGE:
    python scripts/run_e2e_tests.py [options]
    
OPTIONS:
    --bucket NAME           Override test bucket name
    --lambda NAME           Override Lambda function name  
    --region REGION         Override AWS region
    --verbose               Enable verbose output
    --performance-only      Run only performance tests
    --quick                 Run only quick tests (no performance benchmarks)
    --cleanup-only          Only cleanup existing test resources
    --dry-run              Validate environment without running tests

ENVIRONMENT REQUIREMENTS:
    - AWS credentials configured (via AWS CLI, IAM role, or environment variables)
    - S3 bucket accessible for test data
    - Lambda function deployed and accessible
    - Required Python packages installed

WHY THIS SCRIPT:
- Provides pre-flight checks to ensure AWS services are accessible
- Validates test environment before running expensive integration tests
- Offers flexible test execution options for different scenarios
- Handles proper cleanup of test resources
- Provides detailed reporting and error handling
"""

import argparse
import boto3
import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional
import subprocess
import logging

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)


class E2ETestRunner:
    """Comprehensive test runner for WhisperSync end-to-end tests."""
    
    def __init__(self, bucket_name: str, lambda_name: str, region: str = "us-east-1"):
        self.bucket_name = bucket_name
        self.lambda_name = lambda_name
        self.region = region
        self.s3_client = None
        self.lambda_client = None
        
    def validate_environment(self) -> Dict[str, bool]:
        """Validate that all required services and resources are accessible."""
        logger.info("Validating test environment...")
        
        validation_results = {
            "aws_credentials": False,
            "s3_access": False,
            "bucket_exists": False,
            "lambda_exists": False,
            "python_packages": False
        }
        
        # Check AWS credentials
        try:
            session = boto3.Session()
            credentials = session.get_credentials()
            if credentials:
                validation_results["aws_credentials"] = True
                logger.info("✓ AWS credentials found")
            else:
                logger.error("✗ AWS credentials not found")
                return validation_results
        except Exception as e:
            logger.error(f"✗ AWS credentials error: {e}")
            return validation_results
        
        # Initialize AWS clients
        try:
            self.s3_client = boto3.client("s3", region_name=self.region)
            self.lambda_client = boto3.client("lambda", region_name=self.region)
            validation_results["s3_access"] = True
            logger.info("✓ AWS S3 and Lambda clients initialized")
        except Exception as e:
            logger.error(f"✗ AWS client initialization failed: {e}")
            return validation_results
        
        # Check S3 bucket access
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            validation_results["bucket_exists"] = True
            logger.info(f"✓ S3 bucket {self.bucket_name} is accessible")
        except Exception as e:
            logger.error(f"✗ S3 bucket {self.bucket_name} not accessible: {e}")
            logger.info(f"  You may need to create the bucket or check permissions")
        
        # Check Lambda function
        try:
            self.lambda_client.get_function(FunctionName=self.lambda_name)
            validation_results["lambda_exists"] = True
            logger.info(f"✓ Lambda function {self.lambda_name} is accessible")
        except Exception as e:
            logger.warning(f"⚠ Lambda function {self.lambda_name} not accessible: {e}")
            logger.info(f"  Integration tests can still run without Lambda if S3 bucket is accessible")
        
        # Check Python packages
        try:
            import pytest
            import boto3
            import moto
            validation_results["python_packages"] = True
            logger.info("✓ Required Python packages are available")
        except ImportError as e:
            logger.error(f"✗ Missing required Python packages: {e}")
            logger.info("  Run: pip install -r requirements.txt")
        
        return validation_results
    
    def cleanup_test_resources(self) -> int:
        """Clean up any existing test resources from previous runs."""
        logger.info("Cleaning up test resources...")
        
        if not self.s3_client:
            logger.error("S3 client not initialized")
            return 1
        
        cleaned_count = 0
        
        try:
            # List all objects with test prefixes
            test_prefixes = ["transcripts/test_", "outputs/test_", "errors/test_"]
            
            for prefix in test_prefixes:
                paginator = self.s3_client.get_paginator("list_objects_v2")
                pages = paginator.paginate(Bucket=self.bucket_name, Prefix=prefix)
                
                for page in pages:
                    if "Contents" in page:
                        objects_to_delete = [{"Key": obj["Key"]} for obj in page["Contents"]]
                        if objects_to_delete:
                            self.s3_client.delete_objects(
                                Bucket=self.bucket_name,
                                Delete={"Objects": objects_to_delete}
                            )
                            cleaned_count += len(objects_to_delete)
            
            if cleaned_count > 0:
                logger.info(f"✓ Cleaned up {cleaned_count} test objects")
            else:
                logger.info("✓ No test objects to clean up")
            
            return 0
            
        except Exception as e:
            logger.error(f"✗ Cleanup failed: {e}")
            return 1
    
    def run_tests(self, test_options: List[str]) -> int:
        """Run the integration tests with specified options."""
        logger.info("Starting end-to-end integration tests...")
        
        # Prepare pytest command
        pytest_cmd = [
            sys.executable, "-m", "pytest",
            "-c", "pytest-e2e.ini",
            "tests/integration/test_end_to_end.py",
            "-v",
            "--tb=short"
        ]
        
        # Add custom options
        pytest_cmd.extend(test_options)
        
        # Set environment variables
        test_env = os.environ.copy()
        test_env.update({
            "TEST_BUCKET_NAME": self.bucket_name,
            "TEST_LAMBDA_FUNCTION_NAME": self.lambda_name,
            "AWS_DEFAULT_REGION": self.region,
            "TRANSCRIPT_BUCKET_NAME": self.bucket_name
        })
        
        logger.info(f"Running command: {' '.join(pytest_cmd)}")
        
        try:
            # Run tests
            result = subprocess.run(
                pytest_cmd,
                env=test_env,
                cwd=project_root,
                capture_output=False,
                text=True
            )
            
            if result.returncode == 0:
                logger.info("✓ All tests passed!")
            else:
                logger.error(f"✗ Tests failed with exit code {result.returncode}")
            
            return result.returncode
            
        except Exception as e:
            logger.error(f"✗ Test execution failed: {e}")
            return 1
    
    def generate_test_report(self) -> None:
        """Generate a test report with environment information."""
        logger.info("Generating test report...")
        
        report = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
            "environment": {
                "bucket_name": self.bucket_name,
                "lambda_name": self.lambda_name,
                "region": self.region,
                "python_version": sys.version,
                "boto3_version": boto3.__version__
            }
        }
        
        report_file = project_root / "test_report.json"
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"✓ Test report saved to {report_file}")


def main():
    """Main entry point for the test runner."""
    parser = argparse.ArgumentParser(
        description="End-to-End Test Runner for WhisperSync",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/run_e2e_tests.py
  python scripts/run_e2e_tests.py --bucket my-test-bucket --verbose
  python scripts/run_e2e_tests.py --performance-only
  python scripts/run_e2e_tests.py --cleanup-only
  python scripts/run_e2e_tests.py --dry-run
        """
    )
    
    parser.add_argument(
        "--bucket",
        default=os.environ.get("TEST_BUCKET_NAME", "macbook-transcriptions-test"),
        help="S3 bucket name for tests (default: macbook-transcriptions-test)"
    )
    
    parser.add_argument(
        "--lambda",
        default=os.environ.get("TEST_LAMBDA_FUNCTION_NAME", "whispersync-router"),
        help="Lambda function name (default: whispersync-router)"
    )
    
    parser.add_argument(
        "--region",
        default=os.environ.get("AWS_DEFAULT_REGION", "us-east-1"),
        help="AWS region (default: us-east-1)"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output"
    )
    
    parser.add_argument(
        "--performance-only",
        action="store_true",
        help="Run only performance tests"
    )
    
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Run only quick tests (skip performance benchmarks)"
    )
    
    parser.add_argument(
        "--cleanup-only",
        action="store_true",
        help="Only cleanup existing test resources"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate environment without running tests"
    )
    
    args = parser.parse_args()
    
    # Configure logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Debug logging enabled")
    
    # Initialize test runner
    runner = E2ETestRunner(args.bucket, args.lambda, args.region)
    
    try:
        # Validate environment
        validation_results = runner.validate_environment()
        
        # Check critical requirements
        if not validation_results["aws_credentials"]:
            logger.error("AWS credentials are required")
            return 1
        
        if not validation_results["s3_access"]:
            logger.error("S3 access is required")
            return 1
        
        if not validation_results["bucket_exists"]:
            logger.error(f"S3 bucket {args.bucket} must be accessible")
            logger.info("You can create it with: aws s3 mb s3://" + args.bucket)
            return 1
        
        if not validation_results["python_packages"]:
            logger.error("Required Python packages are missing")
            return 1
        
        # Dry run - just validate environment
        if args.dry_run:
            logger.info("✓ Environment validation completed successfully")
            return 0
        
        # Cleanup only
        if args.cleanup_only:
            return runner.cleanup_test_resources()
        
        # Clean up before running tests
        cleanup_result = runner.cleanup_test_resources()
        if cleanup_result != 0:
            logger.warning("Cleanup had issues, but continuing with tests...")
        
        # Prepare test options
        test_options = []
        
        if args.performance_only:
            test_options.extend(["-k", "performance"])
        elif args.quick:
            test_options.extend(["-k", "not performance"])
        
        if args.verbose:
            test_options.append("-vv")
        
        # Run tests
        test_result = runner.run_tests(test_options)
        
        # Generate report
        runner.generate_test_report()
        
        return test_result
        
    except KeyboardInterrupt:
        logger.info("\n\nTest run interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)