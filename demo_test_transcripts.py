#!/usr/bin/env python3
"""
WhisperSync Demo Script - Test All Three Agents

This script creates realistic voice memo transcripts and uploads them to S3
to demonstrate the complete WhisperSync pipeline across all three agent types.
"""

import os
import sys
import time
import json
import boto3
from datetime import datetime
from typing import Dict, List, Any

# Test transcripts for each agent type
DEMO_TRANSCRIPTS = {
    "github_ideas": {
        "raspberry_pi_dashboard.txt": "I want to create a custom dashboard for my Raspberry Pi that my kids can interact with to select games, instead of the normal terminal selection process.",
        
        "ai_expense_tracker.txt": "I have an idea for a personal finance app that uses AI to categorize expenses automatically. It would connect to your bank account, analyze spending patterns, and provide insights on budgeting. Maybe call it SmartBudget or ExpenseAI.",
        
        "voice_workout_coach.txt": "What if we created a voice-activated workout coach that adapts to your fitness level? It could use speech recognition to count reps, provide form feedback, and adjust difficulty in real-time. Think Peloton but for bodyweight exercises.",
        
        "smart_garden_monitor.txt": "I'm thinking about building an IoT garden monitoring system with sensors for soil moisture, temperature, and light levels. It would send notifications to your phone and maybe even auto-water plants when needed.",
        
        "collaborative_playlist.txt": "Here's a cool idea: a collaborative music app where friends can add songs to shared playlists in real-time, vote on what plays next, and see what everyone's listening to. Like a social jukebox for parties."
    },
    
    "work": {
        "authentication_system.txt": "Today I worked on implementing the user authentication system. I completed the login flow, added password reset functionality, and wrote comprehensive unit tests. The feature is now ready for code review. I also identified three performance bottlenecks that we should address next sprint.",
        
        "team_meeting_notes.txt": "Had a productive meeting with the development team about the new API endpoints. We decided to use GraphQL instead of REST for better flexibility. Sarah will lead the frontend integration, Mike will handle the database schema, and I'll work on the authentication middleware.",
        
        "quarterly_review.txt": "Finished preparing for the quarterly review meeting. Our team delivered 85% of planned features, which is above the company average. The main challenges were scope creep on the dashboard project and unexpected technical debt in the legacy system. For next quarter, I'm proposing we allocate 20% of time for refactoring.",
        
        "debugging_session.txt": "Spent most of the day debugging a race condition in the payment processing service. Turns out it was related to database connection pooling. Fixed it by implementing proper connection lifecycle management. This should prevent the intermittent failures we've been seeing in production.",
        
        "code_review_feedback.txt": "Completed code reviews for three pull requests today. Left detailed feedback on the new analytics module - mostly suggestions for better error handling and more descriptive variable names. Also approved the security patch that fixes the OAuth token validation issue."
    },
    
    "memories": {
        "daughter_first_steps.txt": "I remember the day my daughter took her first steps. She was holding onto the coffee table, looked at me with those bright eyes, let go and walked straight into my arms. Pure joy. That moment when she realized she could walk - her face lit up like she had discovered magic.",
        
        "camping_with_dad.txt": "Thinking about that camping trip with dad when I was seven. We sat by the fire and he told me stories about the constellations. He taught me to find the Big Dipper and said that whenever I felt lost, I could look up and find my way home. I still look for it sometimes.",
        
        "first_apartment.txt": "Moving into my first apartment was terrifying and exciting. I remember sitting on the floor eating pizza from a cardboard box because I didn't have furniture yet. But I felt so proud - this tiny studio was mine. I stayed up all night just enjoying the quiet and the freedom.",
        
        "grandmother_cooking.txt": "Grandma teaching me to make her famous apple pie. She never measured anything, just went by feel and taste. 'A pinch of love,' she'd say while adding cinnamon. The kitchen always smelled like home when she cooked. I wish I had written down her recipes.",
        
        "wedding_day_rain.txt": "It rained on our wedding day, but instead of being upset, we danced in the courtyard. Our guests joined us, everyone laughing and spinning in the downpour. The photographer caught the most beautiful shots. Sometimes the unexpected moments become the most precious memories."
    }
}

class WhisperSyncDemo:
    def __init__(self, bucket_name: str = "macbook-transcriptions-development", profile: str = "personal", region: str = "us-east-1"):
        self.bucket_name = bucket_name
        self.profile = profile
        self.region = region
        
        # Initialize AWS session
        self.session = boto3.Session(profile_name=profile, region_name=region)
        self.s3 = self.session.client('s3')
        self.logs = self.session.client('logs')
        
        # Results tracking
        self.results = []
        self.start_time = datetime.now()
        
    def create_transcript_files(self):
        """Create local transcript files for testing."""
        print("📝 Creating transcript files...")
        
        transcript_dir = "demo_transcripts"
        os.makedirs(transcript_dir, exist_ok=True)
        
        for agent_type, transcripts in DEMO_TRANSCRIPTS.items():
            agent_dir = os.path.join(transcript_dir, agent_type)
            os.makedirs(agent_dir, exist_ok=True)
            
            for filename, content in transcripts.items():
                file_path = os.path.join(agent_dir, filename)
                with open(file_path, 'w') as f:
                    f.write(content)
                print(f"  ✅ Created {file_path}")
        
        print(f"📁 All transcript files created in {transcript_dir}/")
        return transcript_dir
    
    def upload_transcript(self, agent_type: str, filename: str, content: str) -> str:
        """Upload a transcript to S3 and return the S3 key."""
        # Create S3 key with date structure
        date_str = datetime.now().strftime("%Y/%m/%d")
        s3_key = f"transcripts/{agent_type}/{date_str}/{filename}"
        
        try:
            self.s3.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=content.encode('utf-8'),
                ContentType='text/plain',
                Metadata={
                    'agent_type': agent_type,
                    'demo_run': 'true',
                    'created_at': datetime.now().isoformat()
                }
            )
            print(f"  📤 Uploaded to s3://{self.bucket_name}/{s3_key}")
            return s3_key
        except Exception as e:
            print(f"  ❌ Upload failed: {e}")
            return None
    
    def wait_for_processing(self, s3_key: str, timeout: int = 30) -> Dict[str, Any]:
        """Wait for Lambda processing and return results."""
        output_key = s3_key.replace("transcripts/", "outputs/").replace(".txt", "_response.json")
        
        print(f"  ⏳ Waiting for processing (checking {output_key})...")
        
        for i in range(timeout):
            try:
                response = self.s3.get_object(Bucket=self.bucket_name, Key=output_key)
                result = json.loads(response['Body'].read().decode('utf-8'))
                print(f"  ✅ Processing complete in {i+1} seconds")
                return result
            except self.s3.exceptions.NoSuchKey:
                time.sleep(1)
            except Exception as e:
                print(f"  ⚠️ Error checking results: {e}")
                time.sleep(1)
        
        print(f"  ⏰ Timeout waiting for processing")
        return {"error": "timeout"}
    
    def get_lambda_logs(self, request_id: str = None) -> List[str]:
        """Get recent Lambda logs."""
        try:
            # Get logs from the last 5 minutes
            start_time = int((datetime.now().timestamp() - 300) * 1000)
            
            response = self.logs.filter_log_events(
                logGroupName='/aws/lambda/mcpAgentRouterLambda-development',
                startTime=start_time,
                filterPattern='ERROR' if request_id else ''
            )
            
            return [event['message'] for event in response.get('events', [])]
        except Exception as e:
            print(f"Could not retrieve logs: {e}")
            return []
    
    def run_agent_test(self, agent_type: str, test_name: str = None) -> Dict[str, Any]:
        """Run a test for a specific agent type."""
        print(f"\n🤖 Testing {agent_type.title()} Agent")
        print("=" * 50)
        
        # Select transcript (use specific test or first available)
        transcripts = DEMO_TRANSCRIPTS[agent_type]
        if test_name and test_name in transcripts:
            filename = test_name
            content = transcripts[test_name]
        else:
            filename = list(transcripts.keys())[0]
            content = transcripts[filename]
        
        print(f"📝 Transcript: {filename}")
        print(f"💬 Content: {content[:100]}{'...' if len(content) > 100 else ''}")
        
        # Upload and process
        s3_key = self.upload_transcript(agent_type, filename, content)
        if not s3_key:
            return {"error": "upload_failed"}
        
        # Wait for processing
        result = self.wait_for_processing(s3_key)
        
        # Store result
        test_result = {
            "agent_type": agent_type,
            "filename": filename,
            "s3_key": s3_key,
            "content": content,
            "result": result,
            "timestamp": datetime.now().isoformat()
        }
        
        self.results.append(test_result)
        return test_result
    
    def run_all_tests(self):
        """Run tests for all three agent types."""
        print("🚀 Starting WhisperSync Demo - Testing All Agents")
        print("=" * 60)
        
        # Test each agent type
        for agent_type in ["github_ideas", "work", "memories"]:
            try:
                result = self.run_agent_test(agent_type)
                
                if "error" not in result:
                    print(f"  ✅ {agent_type} agent test completed successfully")
                else:
                    print(f"  ❌ {agent_type} agent test failed: {result['error']}")
                    
            except Exception as e:
                print(f"  💥 {agent_type} agent test crashed: {e}")
            
            # Brief pause between tests
            time.sleep(2)
    
    def display_results_summary(self):
        """Display a summary of all test results."""
        print("\n📊 WhisperSync Demo Results Summary")
        print("=" * 60)
        
        for i, result in enumerate(self.results, 1):
            agent_type = result['agent_type']
            filename = result['filename']
            
            print(f"\n{i}. {agent_type.title()} Agent - {filename}")
            print(f"   S3 Key: {result['s3_key']}")
            
            if "error" in result['result']:
                print(f"   Status: ❌ Failed ({result['result']['error']})")
            else:
                print(f"   Status: ✅ Success")
                agent_result = result['result']
                if 'message' in agent_result:
                    print(f"   Result: {agent_result['message']}")
                if 'processed_at' in agent_result:
                    print(f"   Processed: {agent_result['processed_at']}")
        
        # Overall statistics
        total_tests = len(self.results)
        successful_tests = len([r for r in self.results if "error" not in r['result']])
        
        print(f"\n📈 Overall Statistics:")
        print(f"   Total Tests: {total_tests}")
        print(f"   Successful: {successful_tests}")
        print(f"   Success Rate: {(successful_tests/total_tests)*100:.1f}%")
        print(f"   Duration: {datetime.now() - self.start_time}")
    
    def save_results(self, filename: str = None):
        """Save detailed results to a JSON file."""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"whispersync_demo_results_{timestamp}.json"
        
        results_data = {
            "demo_info": {
                "timestamp": self.start_time.isoformat(),
                "bucket": self.bucket_name,
                "profile": self.profile,
                "region": self.region
            },
            "test_results": self.results,
            "summary": {
                "total_tests": len(self.results),
                "successful_tests": len([r for r in self.results if "error" not in r['result']]),
                "test_transcripts_used": DEMO_TRANSCRIPTS
            }
        }
        
        with open(filename, 'w') as f:
            json.dump(results_data, f, indent=2)
        
        print(f"💾 Results saved to {filename}")
        return filename
    
    def cleanup_test_data(self):
        """Clean up uploaded test transcripts and outputs."""
        print("\n🧹 Cleaning up test data...")
        
        try:
            # List all objects with today's date
            date_prefix = datetime.now().strftime("%Y/%m/%d")
            
            for prefix in ["transcripts", "outputs"]:
                response = self.s3.list_objects_v2(
                    Bucket=self.bucket_name,
                    Prefix=f"{prefix}/github_ideas/{date_prefix}/"
                )
                
                for obj in response.get('Contents', []):
                    if 'demo' in obj['Key'] or any(name in obj['Key'] for name in DEMO_TRANSCRIPTS['github_ideas'].keys()):
                        self.s3.delete_object(Bucket=self.bucket_name, Key=obj['Key'])
                        print(f"  🗑️ Deleted {obj['Key']}")
            
            print("✅ Cleanup complete")
        except Exception as e:
            print(f"⚠️ Cleanup failed: {e}")


def main():
    """Main demo script entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="WhisperSync Demo - Test all three agents")
    parser.add_argument("--bucket", default="macbook-transcriptions-development", help="S3 bucket name")
    parser.add_argument("--profile", default="personal", help="AWS profile")
    parser.add_argument("--region", default="us-east-1", help="AWS region")
    parser.add_argument("--agent", choices=["github_ideas", "work", "memories"], help="Test specific agent only")
    parser.add_argument("--transcript", help="Specific transcript filename to test")
    parser.add_argument("--create-files", action="store_true", help="Only create transcript files, don't upload")
    parser.add_argument("--cleanup", action="store_true", help="Clean up test data from S3")
    parser.add_argument("--no-cleanup", action="store_true", help="Don't clean up after tests")
    
    args = parser.parse_args()
    
    # Initialize demo
    demo = WhisperSyncDemo(bucket_name=args.bucket, profile=args.profile, region=args.region)
    
    # Handle specific actions
    if args.create_files:
        demo.create_transcript_files()
        return
    
    if args.cleanup:
        demo.cleanup_test_data()
        return
    
    # Run tests
    if args.agent:
        # Test specific agent
        demo.run_agent_test(args.agent, args.transcript)
    else:
        # Run all tests
        demo.run_all_tests()
    
    # Display and save results
    demo.display_results_summary()
    demo.save_results()
    
    # Cleanup unless disabled
    if not args.no_cleanup:
        demo.cleanup_test_data()
    
    print("\n🎉 WhisperSync Demo Complete!")
    print("Your voice-to-action cognitive exoskeleton is working! 🎙️→🤖→⚡")


if __name__ == "__main__":
    main()