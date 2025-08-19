# Agriculture AI - Voice-to-AI Pipeline

A comprehensive AI-powered agriculture advisory system that processes voice calls through Asterisk, transcribes them, and provides intelligent responses in local languages using LLM services.

## 🌾 Overview

This project creates an Interactive Voice Response (IVR) system that:
1. Receives voice calls through Asterisk PBX
2. Records and transcribes conversations
3. Processes queries using specialized AI agents (Weather, Soil, Pest, Scheme)
4. Generates responses in local languages
5. Converts responses back to audio for playback

## 📋 Prerequisites

- Docker and Docker Compose
- Python 3.8+
- Zoiper5 SoftPhone application
- OpenRouter.ai API key
- macOS (tested environment)

## 🚀 Setup Instructions

### Step 1: Get OpenRouter.ai API Key

1. Visit [OpenRouter.ai](https://openrouter.ai)
2. Create an account and generate an API key
3. Replace the API key in `LLM_Server/llm_client.py`:
   ```python
   api_key="YOUR_OPENROUTER_API_KEY_HERE"
   ```

### Step 2: Install Zoiper5 SoftPhone

1. Download Zoiper5 from [https://www.zoiper.com/en/voip-softphone/download/current](https://www.zoiper.com/en/voip-softphone/download/current)
2. Install the application on your system
3. Launch Zoiper5

### Step 3: Configure Zoiper5

1. Open Zoiper5 and click on "Settings" or "Preferences"
2. Navigate to "Accounts" → "Add Account"
3. Select "SIP" as the protocol
4. Configure the account with these settings:
   - **Username**: `6001`
   - **Password**: `6001` 
   - **Domain/Hostname**: `localhost`
   - **Port**: `5060`
   - **Account Type**: Free user
5. Click "Create Account" and verify it registers successfully
6. You should see a green status indicating the account is registered

### Step 4: Start Docker Container

1. Navigate to the project directory:
   ```bash
   cd /Users/apple/Desktop/Agricultre_AI
   ```

2. Start the Asterisk container using Docker Compose:
   ```bash
   docker-compose up -d
   ```

3. Verify the container is running:
   ```bash
   docker ps
   ```

4. Check container logs to ensure proper startup:
   ```bash
   docker logs asterisk-server
   ```

### Step 5: Start Audio Processing Pipelines

1. **Start the Audio Fetcher Pipeline** (in a new terminal):
   ```bash
   cd /Users/apple/Desktop/Agricultre_AI
   source venv/bin/activate && src/audio_fetcher.py
   ```

2. **Start the Transcript Monitor Pipeline** (in another new terminal):
   ```bash
   cd /Users/apple/Desktop/Agricultre_AI
   source venv/bin/activate && transcript_monitor.py
   ```

### Step 6: Test the System

#### Make a Test Call

1. In Zoiper5, dial `9999` and press call
2. Wait for the call to connect
3. **Wait 3 seconds** after connection
4. Start speaking your agriculture-related query in your preferred language
5. Speak clearly for 10-15 seconds
6. Hang up the call

#### Verify Recording

1. In Zoiper5, dial `1000` and press call
2. Listen to your entire recorded conversation
3. Verify it was captured properly
4. Hang up when finished

#### Check AI Response

1. Wait 1-2 minutes for AI processing to complete
2. Check the generated audio directory:
   ```bash
   ls -la recordings/generated_audio/
   ```
3. Play the latest audio file to hear the AI response in your local language

## 🏗️ System Architecture

### Components

1. **Asterisk PBX**: Handles SIP calls and recording
2. **Audio Fetcher**: Monitors and processes new recordings
3. **Transcript Monitor**: Processes transcripts through AI agents
4. **LLM Server**: Contains specialized AI agents:
   - Weather Agent
   - Soil Agent  
   - Pest Agent
   - Scheme Agent
   - Orchestrator Agent

### Workflow

```
Voice Call → Asterisk → Recording → Audio Fetcher → Transcription
                                                        ↓
AI Response ← Text-to-Speech ← LLM Agents ← Transcript Monitor
```

## 📞 Key Phone Numbers

- **9999**: Record a new query (speak after 3 seconds)
- **1000**: Playback last recording for verification

## 📁 Project Structure

```
Agriculture_AI/
├── docker-compose.yml          # Docker services configuration
├── Dockerfile.processor        # Recording processor container
├── transcript_monitor.py       # AI transcript processing pipeline
├── monitor_recordings.sh       # Log monitoring script
│
├── src/                        # 🐍 Python source code
│   ├── audio_fetcher.py       # Audio monitoring and fetching
│   ├── recording_processor.py  # Audio transcription processor
│   └── tts_generator.py       # Text-to-speech generator
│
├── LLM_Server/                # 🤖 AI Agents and Services
│   ├── llm_client.py          # OpenRouter API client
│   ├── orchestrator_agent.py  # Main AI coordinator
│   ├── weather_agent.py       # Weather advice agent
│   ├── soil_agent.py          # Soil analysis agent
│   ├── pest_agent.py          # Pest management agent
│   └── scheme_agent.py        # Government schemes agent
│
├── config/                    # ⚙️ Configuration files
│   ├── requirements.txt       # Python dependencies
│   ├── processor_config.json  # Processing configuration
│   └── credentials.json       # API credentials
│
├── recordings/                # 🎵 Audio processing directories
│   ├── raw/                   # Original recordings
│   ├── converted/             # Converted audio files
│   ├── transcripts/           # Generated transcripts
│   ├── responses/             # AI text responses
│   └── generated_audio/       # AI audio responses (🎯 CHECK HERE)
│
├── etc/asterisk/              # ⚙️ Asterisk PBX configuration
├── logs/                      # � Application and system logs
└── sounds/                    # 🔊 Audio assets and prompts
```

## 🔧 Troubleshooting

### Docker Issues
- Ensure Docker is running: `docker ps`
- Restart container: `docker-compose restart`
- Check logs: `docker logs asterisk-server`

### Zoiper5 Connection Issues
- Verify localhost connectivity
- Check if port 5060 is available: `netstat -an | grep 5060`
- Restart Zoiper5 and re-register account

### Audio Pipeline Issues
- Check if Python dependencies are installed
- Verify file permissions in recordings directory
- Monitor logs in `logs/` directory for errors

### No AI Response Generated
- Verify OpenRouter.ai API key is correct and active
- Check internet connectivity
- Monitor `transcript_monitor.py` logs for processing errors
- Ensure all required Python packages are installed

### API Key Configuration
The API key needs to be replaced in `LLM_Server/llm_client.py` around line 17:
```python
api_key="sk-or-v1-YOUR_NEW_API_KEY_HERE"
```

## 🎯 Expected Results

After following all steps and making a test call:

1. **Audio Recording**: Your voice query should be saved in `recordings/raw/`
2. **Transcription**: Text transcript should appear in `recordings/transcripts/`
3. **AI Processing**: The AI agents will analyze your agriculture query
4. **Response Generation**: An audio response will be created in `recordings/generated_audio/`
5. **Local Language**: The response will be in your preferred local language

## 🌐 Supported Languages

The system supports multiple languages for both input and output through Google's speech services and LLM translation capabilities.

## � Development Notes

- This system is designed for agriculture-focused queries
- AI agents provide advice on weather, soil, pests, and government schemes
- All responses are tailored to local agricultural practices
- The system maintains conversation context for follow-up questions

## 🐳 Docker Services

### Asterisk Server
- **Image**: `andrius/asterisk:latest`
- **Ports**: SIP (5060), RTP (10000-10099), IAX2 (4569), AMI (5038), HTTP (8088)
- **Function**: VoIP server for call handling and recording

### Recording Processor
- **Custom Build**: Based on Python 3.11
- **Function**: Monitors and processes recordings automatically
- **Features**: 
  - Real-time file monitoring
  - Speech-to-text conversion
  - Multi-language translation
  - Text-to-speech generation

## 🎯 Key Features

### 🎤 Speech Processing
- **Google Cloud Speech-to-Text**: High-accuracy transcription
- **Auto Language Detection**: Supports 100+ languages
- **Multiple Audio Formats**: WAV, MP3, M4A, FLAC, OGG, GSM

### 🌍 Translation
- **Google Cloud Translation**: Professional-grade translation
- **100+ Language Support**: Automatic language pair detection
- **Batch Processing**: Efficient handling of multiple files

### 🔊 Text-to-Speech
- **Google Cloud TTS**: Natural-sounding voice synthesis
- **Neural Voice Models**: High-quality audio generation
- **Multiple Voice Options**: Various languages and accents

### 🔄 Real-time Monitoring
- **Watchdog Integration**: Automatic file detection
- **Docker Volume Monitoring**: Tracks container recordings
- **Live Processing**: Immediate handling of new recordings

## 🛠️ Management Commands

### Service Control
```bash
# Start Docker services
docker-compose up -d

# Stop services
docker-compose down

# View service status
docker ps

# View live logs
docker logs asterisk-server -f
```

### Pipeline Management
```bash
# Start audio fetcher (Terminal 1)
python3 src/audio_fetcher.py

# Start transcript monitor (Terminal 2)
python3 transcript_monitor.py

# Monitor LLM server logs
tail -f LLM_Server/logs/*.log
```

## 🔧 Configuration Files

### Key Configuration Files
- **LLM Client**: `LLM_Server/llm_client.py` (Update OpenRouter API key here)
- **Docker Compose**: `docker-compose.yml` (Service definitions)
- **Asterisk Config**: `etc/asterisk/` (PBX configuration)
- **Credentials**: `config/credentials.json` (Google Cloud credentials)

### OpenRouter API Configuration
```python
# In LLM_Server/llm_client.py
self.client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key="sk-or-v1-YOUR_API_KEY_HERE"  # Replace this line
)
```

## 🤖 AI Agents

### Weather Agent
- Provides weather forecasts and advisories
- Offers climate-based farming recommendations
- Suggests optimal planting and harvesting times

### Soil Agent
- Analyzes soil health and composition
- Recommends fertilizers and soil treatments
- Provides irrigation and drainage advice

### Pest Agent
- Identifies common agricultural pests
- Suggests organic and chemical control methods
- Offers prevention strategies

### Scheme Agent
- Information about government agricultural schemes
- Subsidy and loan program details
- Application processes and eligibility criteria

### Orchestrator Agent
- Routes queries to appropriate specialist agents
- Combines responses from multiple agents
- Ensures comprehensive agriculture advice

## 📊 Monitoring and Logging

### Log Locations
- **Audio Fetcher**: `src/audio_fetcher.py` console output
- **Transcript Monitor**: `transcript_monitor.py` console output
- **Asterisk**: `logs/messages`
- **LLM Processing**: `LLM_Server/logs/`

### Monitoring Commands
```bash
# Monitor all logs
tail -f logs/* LLM_Server/logs/*

# Check recording processing
ls -la recordings/*/

# Monitor Docker container
docker logs asterisk-server --follow
```

## 🔄 Complete Workflow Example

1. **Setup Phase**:
   ```bash
   # Get OpenRouter API key and update llm_client.py
   # Install and configure Zoiper5 with localhost:5060
   # Start Docker container
   docker-compose up -d
   ```

2. **Start Pipelines**:
   ```bash
   # Terminal 1: Audio processing
   python3 src/audio_fetcher.py
   
   # Terminal 2: AI processing  
   python3 transcript_monitor.py
   ```

3. **Make Test Call**:
   ```bash
   # In Zoiper5: Dial 9999
   # Wait 3 seconds, then speak agriculture query
   # Example: "What is the best time to plant wheat in my region?"
   ```

4. **Verify Recording**:
   ```bash
   # In Zoiper5: Dial 1000
   # Listen to complete recording
   ```

5. **Check AI Response**:
   ```bash
   # Wait 1-2 minutes, then check:
   ls -la recordings/generated_audio/
   # Play the latest .wav file
   ```

## 🚨 Troubleshooting Guide

### Zoiper5 Issues
**Problem**: Cannot connect to localhost
```bash
# Check if Asterisk is running
docker ps | grep asterisk

# Verify port 5060 is accessible
telnet localhost 5060

# Restart Asterisk container
docker-compose restart
```

### Pipeline Issues
**Problem**: Audio fetcher not processing files
```bash
# Check file permissions
ls -la recordings/raw/

# Verify monitor directory exists
ls -la monitor/

# Check Python dependencies
pip3 install -r config/requirements.txt
```

**Problem**: No AI response generated
```bash
# Verify OpenRouter API key
curl -H "Authorization: Bearer sk-or-v1-YOUR_KEY" https://openrouter.ai/api/v1/models

# Check transcript files exist
ls -la recordings/transcripts/

# Monitor transcript_monitor.py output for errors
```

### Audio Issues
**Problem**: No recording created
```bash
# Check Asterisk dialplan configuration
docker exec -it asterisk-server asterisk -rx "dialplan show"

# Verify recording permissions
ls -la recordings/

# Check Asterisk CLI
docker exec -it asterisk-server asterisk -r
```

## 🎯 Testing Scenarios

### Basic Agriculture Queries
- "What's the weather forecast for farming this week?"
- "My crops have yellow leaves, what should I do?"
- "Which government schemes are available for farmers?"
- "When should I plant tomatoes in my region?"

### Multi-language Testing
- Test queries in Hindi, Telugu, Tamil, or other local languages
- Verify responses are generated in the same language
- Check audio quality of local language TTS

## 📱 Production Deployment

### Security Considerations
- Replace default Asterisk passwords
- Use HTTPS for web interfaces
- Implement firewall rules for SIP ports
- Secure OpenRouter API keys

### Scaling Options
- Use multiple Asterisk instances for high call volume
- Implement load balancing for AI agents
- Add Redis caching for frequently asked questions
- Use database storage for conversation history

## 🎓 Educational Use

This system serves as an excellent example of:
- **VoIP Integration**: Asterisk PBX setup and configuration
- **AI Pipeline Development**: Multi-stage processing workflows  
- **Microservices Architecture**: Docker-based service coordination
- **Speech Processing**: STT, TTS, and natural language processing
- **Agriculture Technology**: Domain-specific AI applications