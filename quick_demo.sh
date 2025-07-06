#!/bin/bash
# WhisperSync Quick Demo Script
# 
# This script provides easy commands to test your WhisperSync system

set -e

BUCKET="macbook-transcriptions-development"
PROFILE="personal"
REGION="us-east-1"

echo "🎙️ WhisperSync Quick Demo"
echo "========================="

function show_usage() {
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  all          - Test all three agents (default)"
    echo "  github       - Test GitHub Ideas agent only"
    echo "  work         - Test Work Journal agent only"
    echo "  memories     - Test Memory agent only"
    echo "  files        - Create demo transcript files only"
    echo "  logs         - Show recent Lambda logs"
    echo "  results      - Show recent S3 outputs"
    echo "  cleanup      - Clean up test data"
    echo "  status       - Check system health"
    echo ""
    echo "Examples:"
    echo "  $0 all           # Test all agents"
    echo "  $0 github        # Test GitHub agent with Pi dashboard idea"
    echo "  $0 work          # Test work agent with auth system notes"
}

function test_github_agent() {
    echo "🤖 Testing GitHub Ideas Agent..."
    echo "Idea: Custom Raspberry Pi dashboard for kids game selection"
    
    cat > temp_github_test.txt << EOF
I want to create a custom dashboard for my Raspberry Pi that my kids can interact with to select games, instead of the normal terminal selection process. It should have big colorful buttons, maybe some fun animations, and be touch-screen friendly.
EOF
    
    aws s3 cp temp_github_test.txt s3://$BUCKET/transcripts/github_ideas/2025/07/04/quick_demo_github.txt --profile $PROFILE --region $REGION
    echo "📤 Uploaded to S3, processing..."
    sleep 3
    
    # Check for output
    if aws s3 cp s3://$BUCKET/outputs/github_ideas/2025/07/04/quick_demo_github_response.json . --profile $PROFILE --region $REGION 2>/dev/null; then
        echo "✅ GitHub agent processed successfully!"
        echo "📄 Response:"
        cat quick_demo_github_response.json | jq '.' 2>/dev/null || cat quick_demo_github_response.json
        rm -f quick_demo_github_response.json
    else
        echo "⏳ Still processing or failed. Check logs with: $0 logs"
    fi
    
    rm -f temp_github_test.txt
}

function test_work_agent() {
    echo "🤖 Testing Work Journal Agent..."
    echo "Work note: Authentication system completion"
    
    cat > temp_work_test.txt << EOF
Today I completed the user authentication system for the new app. Implemented OAuth2 integration, added password reset functionality, and wrote comprehensive unit tests. The feature is ready for code review. Also identified three performance bottlenecks in the database queries that we should address next sprint.
EOF
    
    aws s3 cp temp_work_test.txt s3://$BUCKET/transcripts/work/2025/07/04/quick_demo_work.txt --profile $PROFILE --region $REGION
    echo "📤 Uploaded to S3, processing..."
    sleep 3
    
    # Check for output
    if aws s3 cp s3://$BUCKET/outputs/work/2025/07/04/quick_demo_work_response.json . --profile $PROFILE --region $REGION 2>/dev/null; then
        echo "✅ Work agent processed successfully!"
        echo "📄 Response:"
        cat quick_demo_work_response.json | jq '.' 2>/dev/null || cat quick_demo_work_response.json
        rm -f quick_demo_work_response.json
    else
        echo "⏳ Still processing or failed. Check logs with: $0 logs"
    fi
    
    rm -f temp_work_test.txt
}

function test_memory_agent() {
    echo "🤖 Testing Memory Agent..."
    echo "Memory: Daughter's first steps"
    
    cat > temp_memory_test.txt << EOF
I remember the day my daughter took her first steps. She was holding onto the coffee table, looked at me with those bright eyes, let go and walked straight into my arms. Pure joy. That moment when she realized she could walk - her face lit up like she had discovered magic.
EOF
    
    aws s3 cp temp_memory_test.txt s3://$BUCKET/transcripts/memories/2025/07/04/quick_demo_memory.txt --profile $PROFILE --region $REGION
    echo "📤 Uploaded to S3, processing..."
    sleep 3
    
    # Check for output
    if aws s3 cp s3://$BUCKET/outputs/memories/2025/07/04/quick_demo_memory_response.json . --profile $PROFILE --region $REGION 2>/dev/null; then
        echo "✅ Memory agent processed successfully!"
        echo "📄 Response:"
        cat quick_demo_memory_response.json | jq '.' 2>/dev/null || cat quick_demo_memory_response.json
        rm -f quick_demo_memory_response.json
    else
        echo "⏳ Still processing or failed. Check logs with: $0 logs"
    fi
    
    rm -f temp_memory_test.txt
}

function show_logs() {
    echo "📋 Recent Lambda logs..."
    aws logs filter-log-events \
        --log-group-name /aws/lambda/mcpAgentRouterLambda-development \
        --start-time $(date -d '10 minutes ago' +%s)000 \
        --profile $PROFILE \
        --region $REGION \
        --query 'events[*].message' \
        --output text | tail -20
}

function show_results() {
    echo "📁 Recent S3 outputs..."
    aws s3 ls s3://$BUCKET/outputs/ --recursive --profile $PROFILE --region $REGION | tail -10
}

function cleanup_test_data() {
    echo "🧹 Cleaning up test data..."
    
    # Clean up demo files from today
    DATE_PREFIX=$(date +%Y/%m/%d)
    
    for agent in github_ideas work memories; do
        echo "Cleaning $agent demos..."
        aws s3 rm s3://$BUCKET/transcripts/$agent/$DATE_PREFIX/ --recursive --exclude "*" --include "*quick_demo*" --profile $PROFILE --region $REGION 2>/dev/null || true
        aws s3 rm s3://$BUCKET/outputs/$agent/$DATE_PREFIX/ --recursive --exclude "*" --include "*quick_demo*" --profile $PROFILE --region $REGION 2>/dev/null || true
    done
    
    echo "✅ Cleanup complete"
}

function check_status() {
    echo "🏥 System Health Check..."
    
    echo "1. AWS Credentials:"
    if aws sts get-caller-identity --profile $PROFILE --region $REGION > /dev/null 2>&1; then
        echo "   ✅ AWS credentials working"
    else
        echo "   ❌ AWS credentials failed"
        return 1
    fi
    
    echo "2. S3 Bucket:"
    if aws s3 ls s3://$BUCKET --profile $PROFILE --region $REGION > /dev/null 2>&1; then
        echo "   ✅ S3 bucket accessible"
    else
        echo "   ❌ S3 bucket not accessible"
        return 1
    fi
    
    echo "3. Lambda Function:"
    if aws lambda get-function --function-name mcpAgentRouterLambda-development --profile $PROFILE --region $REGION > /dev/null 2>&1; then
        echo "   ✅ Lambda function exists"
    else
        echo "   ❌ Lambda function not found"
        return 1
    fi
    
    echo "4. GitHub Token:"
    if aws secretsmanager get-secret-value --secret-id github/personal_token --profile $PROFILE --region $REGION > /dev/null 2>&1; then
        echo "   ✅ GitHub token configured"
    else
        echo "   ⚠️ GitHub token not configured"
    fi
    
    echo ""
    echo "🎉 WhisperSync system is operational!"
}

function create_demo_files() {
    echo "📝 Creating demo transcript files..."
    python demo_test_transcripts.py --create-files
}

# Main script logic
case "${1:-all}" in
    "all")
        echo "🚀 Testing all three agents..."
        test_github_agent
        echo ""
        test_work_agent
        echo ""
        test_memory_agent
        echo ""
        echo "🎉 All agents tested! Your cognitive exoskeleton is working!"
        ;;
    "github")
        test_github_agent
        ;;
    "work")
        test_work_agent
        ;;
    "memories")
        test_memory_agent
        ;;
    "files")
        create_demo_files
        ;;
    "logs")
        show_logs
        ;;
    "results")
        show_results
        ;;
    "cleanup")
        cleanup_test_data
        ;;
    "status")
        check_status
        ;;
    "help"|"-h"|"--help")
        show_usage
        ;;
    *)
        echo "❌ Unknown command: $1"
        show_usage
        exit 1
        ;;
esac