#!/usr/bin/env python3
"""
Cleanup script for integration test resources.
Removes test objects from S3 to prevent resource accumulation.
"""

import argparse
import boto3
import sys
from datetime import datetime, timedelta


def cleanup_s3_objects(bucket_name, prefix, dry_run=False):
    """
    Clean up S3 objects with the given prefix.
    
    Args:
        bucket_name: S3 bucket name
        prefix: Object prefix to filter
        dry_run: If True, only print what would be deleted
    """
    s3 = boto3.client('s3')
    
    try:
        # List objects with prefix
        paginator = s3.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=bucket_name, Prefix=prefix)
        
        objects_to_delete = []
        for page in pages:
            if 'Contents' in page:
                for obj in page['Contents']:
                    objects_to_delete.append({'Key': obj['Key']})
                    if dry_run:
                        print(f"Would delete: {obj['Key']}")
        
        if not objects_to_delete:
            print(f"No objects found with prefix: {prefix}")
            return
        
        if dry_run:
            print(f"\nDry run complete. Would delete {len(objects_to_delete)} objects.")
        else:
            # Delete objects in batches of 1000 (S3 limit)
            for i in range(0, len(objects_to_delete), 1000):
                batch = objects_to_delete[i:i+1000]
                response = s3.delete_objects(
                    Bucket=bucket_name,
                    Delete={'Objects': batch}
                )
                
                if 'Errors' in response:
                    print(f"Errors during deletion: {response['Errors']}")
                else:
                    print(f"Successfully deleted {len(batch)} objects")
                    
    except Exception as e:
        print(f"Error during cleanup: {e}")
        sys.exit(1)


def cleanup_old_test_resources(bucket_name, days_old=7, dry_run=False):
    """
    Clean up test resources older than specified days.
    
    Args:
        bucket_name: S3 bucket name
        days_old: Delete resources older than this many days
        dry_run: If True, only print what would be deleted
    """
    s3 = boto3.client('s3')
    cutoff_date = datetime.now() - timedelta(days=days_old)
    
    try:
        # List all objects
        paginator = s3.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=bucket_name, Prefix='integration-tests-')
        
        objects_to_delete = []
        for page in pages:
            if 'Contents' in page:
                for obj in page['Contents']:
                    if obj['LastModified'].replace(tzinfo=None) < cutoff_date:
                        objects_to_delete.append({'Key': obj['Key']})
                        if dry_run:
                            print(f"Would delete old object: {obj['Key']} (Last modified: {obj['LastModified']})")
        
        if not objects_to_delete:
            print(f"No old test objects found (older than {days_old} days)")
            return
        
        if dry_run:
            print(f"\nDry run complete. Would delete {len(objects_to_delete)} old objects.")
        else:
            # Delete objects
            for i in range(0, len(objects_to_delete), 1000):
                batch = objects_to_delete[i:i+1000]
                s3.delete_objects(
                    Bucket=bucket_name,
                    Delete={'Objects': batch}
                )
                print(f"Deleted {len(batch)} old test objects")
                
    except Exception as e:
        print(f"Error during old resource cleanup: {e}")


def main():
    parser = argparse.ArgumentParser(description='Clean up integration test resources')
    parser.add_argument('--bucket', required=True, help='S3 bucket name')
    parser.add_argument('--prefix', help='Object prefix to delete')
    parser.add_argument('--days-old', type=int, default=7, 
                       help='Delete test resources older than this many days (default: 7)')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Show what would be deleted without actually deleting')
    
    args = parser.parse_args()
    
    if args.prefix:
        print(f"Cleaning up objects with prefix: {args.prefix}")
        cleanup_s3_objects(args.bucket, args.prefix, args.dry_run)
    
    # Always clean up old test resources
    print(f"\nCleaning up test resources older than {args.days_old} days...")
    cleanup_old_test_resources(args.bucket, args.days_old, args.dry_run)


if __name__ == '__main__':
    main()