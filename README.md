# Asterisk Recording Processor

A comprehensive solution for processing Asterisk call recordings with automatic speech-to-text, translation, and text-to-speech capabilities using Google Cloud APIs.

## 🚀 Quick Start

### One-Command Setup
```bash
./run.sh
```

This single command will:
- ✅ Check and install prerequisites
- ✅ Set up Python environment with dependencies
- ✅ Configure Google Cloud credentials
- ✅ Build and start Docker containers
- ✅ Start automatic recording monitoring
- ✅ Run system health checks

## 📁 Project Structure

```
asterisk/
├── run.sh                      # 🎯 Main setup and runner script
├── docker-compose.yml          # Docker services configuration
├── Dockerfile.processor        # Recording processor container
├── .env                        # Environment variables
├── monitor_recordings.sh       # Log monitoring script
├── test_system.py             # System validation script
│
├── src/                        # 🐍 Python source code
│   ├── recording_processor_google.py  # Main processor with Google Cloud APIs
│   ├── start_monitoring.py           # Enhanced monitoring service
│   └── tts_generator.py              # Text-to-speech generator
│
├── config/                     # ⚙️ Configuration files
│   ├── requirements.txt       # Python dependencies
│   └── processor_config.json  # Processing configuration
│
├── recordings/                 # 🎵 Audio processing directories
│   ├── raw/                   # Input recordings
│   ├── converted/             # Converted audio files
│   ├── transcripts/           # Generated transcripts
│   └── generated_audio/       # TTS output
│
├── monitor/                    # 👁️ Docker container monitoring
├── logs/                       # 📊 Application logs
├── etc/asterisk/              # ⚙️ Asterisk configuration
└── sounds/                     # 🔊 Audio assets
```

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
# Start all services
./run.sh

# Stop all services
./run.sh --stop

# View service status
./run.sh --status

# View live logs
./run.sh --logs

# Monitor processing logs
./monitor_recordings.sh
```

### Docker Commands
```bash
# Manual service management
docker-compose up -d              # Start services
docker-compose down               # Stop services
docker-compose restart           # Restart services
docker-compose logs -f            # View logs

# Individual service control
docker-compose restart asterisk
docker-compose restart recording-processor
```

### Development Commands
```bash
# Test system health
./test_system.py

# Check Google Cloud credentials
python src/recording_processor_google.py --test

# Show system status
python src/recording_processor_google.py --status

# Generate TTS audio interactively
python src/tts_generator.py --interactive

# Process existing files manually
python src/recording_processor_google.py
```

## 🔧 Configuration

### Environment Variables (.env)
```bash
# Google Cloud API
GOOGLE_CLOUD_API_KEY=your_api_key_here
GOOGLE_CLOUD_PROJECT_ID=your_project_id

# Container Settings
CONTAINER_NAME=asterisk-server
ASTERISK_IMAGE=andrius/asterisk:latest

# Port Configuration
SIP_PORT=5060
RTP_PORT_RANGE_START=10000
RTP_PORT_RANGE_END=10099
```

### Google Cloud Setup
1. Create a Google Cloud Project
2. Enable required APIs:
   - Cloud Speech-to-Text API
   - Cloud Translation API
   - Cloud Text-to-Speech API
3. Generate an API key
4. Update `.env` file with your credentials

## 📊 Monitoring and Logging

### Processing Logs
- **Location**: `recordings/processor.log`
- **Live Monitoring**: `./monitor_recordings.sh`
- **Docker Logs**: `docker-compose logs recording-processor`

### Service Health
- **Asterisk Health**: HTTP endpoint on port 8088
- **Processor Health**: File-based health checks
- **Automatic Restart**: Services restart on failure

## 🔄 Workflow

1. **Recording Creation**: Asterisk creates call recordings
2. **File Detection**: Monitoring service detects new files
3. **Audio Conversion**: Files converted to optimal format
4. **Speech Recognition**: Audio transcribed to text
5. **Language Detection**: Source language identified
6. **Translation**: Text translated if needed
7. **Output Generation**: Results saved as JSON/text
8. **TTS Generation**: Optional audio synthesis

## 🚨 Troubleshooting

### Common Issues

**Services won't start**
```bash
# Check Docker status
docker info

# View detailed logs
docker-compose logs

# Restart services
./run.sh --stop && ./run.sh
```

**Processing not working**
```bash
# Check Google Cloud credentials
./run.sh --test

# Check file permissions
ls -la recordings/

# Monitor processing logs
./monitor_recordings.sh
```

**Port conflicts**
```bash
# Check port usage
netstat -tlnp | grep :5060

# Modify ports in .env file
SIP_PORT=5061
```

### Log Files
- **Setup**: `setup.log`
- **Processing**: `recordings/processor.log`
- **Asterisk**: `logs/messages`
- **Docker**: `docker-compose logs`

## 🎛️ Advanced Configuration

### Custom Asterisk Configuration
- Edit files in `etc/asterisk/`
- Restart Asterisk: `docker-compose restart asterisk`

### Processing Parameters
- Modify `config/processor_config.json`
- Adjust language settings in `.env`
- Configure TTS voices and quality

### Performance Tuning
- Adjust RTP port range for concurrent calls
- Scale processing containers: `docker-compose up -d --scale recording-processor=3`
- Optimize audio settings for quality vs. speed

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test with `./run.sh --test`
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

- **Documentation**: See `docs/` folder
- **Issues**: Check `docs/TROUBLESHOOTING.md`
- **Logs**: Run `./monitor_recordings.sh`

---

**Ready to process your recordings? Just run `./run.sh` and you're good to go!** 🎉
