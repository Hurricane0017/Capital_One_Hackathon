#!/bin/bash

# Monitor Recording Processor Logs
# This script provides real-time monitoring of the recording processing system

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${BLUE}🎵 Asterisk Recording Processor Monitor${NC}"
echo -e "${CYAN}=======================================${NC}"
echo ""
echo -e "${YELLOW}Monitoring Options:${NC}"
echo "1. Recording Processor Logs (Live)"
echo "2. All Services Logs"
echo "3. Service Status"
echo "4. Recent Processing Activity"
echo "5. Exit"
echo ""

read -p "Select option (1-5): " choice

case $choice in
    1)
        echo -e "${GREEN}📊 Monitoring Recording Processor Logs...${NC}"
        echo -e "${CYAN}Press Ctrl+C to stop${NC}"
        echo ""
        docker-compose logs -f recording-processor
        ;;
    2)
        echo -e "${GREEN}📊 Monitoring All Service Logs...${NC}"
        echo -e "${CYAN}Press Ctrl+C to stop${NC}"
        echo ""
        docker-compose logs -f
        ;;
    3)
        echo -e "${GREEN}📋 Service Status:${NC}"
        echo ""
        docker-compose ps
        echo ""
        echo -e "${GREEN}📊 Resource Usage:${NC}"
        docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}"
        ;;
    4)
        echo -e "${GREEN}📁 Recent Processing Activity:${NC}"
        echo ""
        if [ -f "recordings/processor.log" ]; then
            echo -e "${CYAN}Last 20 log entries:${NC}"
            tail -20 recordings/processor.log
        else
            echo "No processor log found yet."
        fi
        
        echo ""
        echo -e "${CYAN}Processed Files:${NC}"
        if [ -f "recordings/processed_files.json" ]; then
            python3 -c "
import json
try:
    with open('recordings/processed_files.json', 'r') as f:
        data = json.load(f)
    print(f'Total processed files: {len(data)}')
    if data:
        print('Recent files:')
        for item in list(data.items())[-5:]:
            print(f'  - {item[0]}: {item[1].get(\"status\", \"unknown\")}')
except:
    print('No processed files data available')
" 2>/dev/null || echo "No processed files data available"
        fi
        
        echo ""
        echo -e "${CYAN}Directory Status:${NC}"
        echo "Raw recordings: $(ls -1 recordings/raw 2>/dev/null | wc -l | tr -d ' ') files"
        echo "Transcripts: $(ls -1 recordings/transcripts 2>/dev/null | wc -l | tr -d ' ') files"
        echo "Converted audio: $(ls -1 recordings/converted 2>/dev/null | wc -l | tr -d ' ') files"
        echo "Generated audio: $(ls -1 recordings/generated_audio 2>/dev/null | wc -l | tr -d ' ') files"
        ;;
    5)
        echo -e "${GREEN}👋 Goodbye!${NC}"
        exit 0
        ;;
    *)
        echo -e "${YELLOW}⚠️  Invalid option. Please select 1-5.${NC}"
        ;;
esac
