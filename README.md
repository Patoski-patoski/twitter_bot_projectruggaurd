# 🔍 Project RUGGUARD - Twitter Bot

**A comprehensive Twitter bot that analyzes account trustworthiness for the Solana DeFi community.**

## 🎯 Mission

Project RUGGUARD helps users assess the trustworthiness of token projects and accounts on the Solana Network by providing automated analysis reports when triggered with the phrase "riddle me this" in replies.

## ✨ Features

- **🔍 Automated Account Analysis**: Analyzes account age, follower ratios, bio content, and engagement patterns
- **🤝 Trusted Network Verification**: Cross-references accounts against a curated list of trusted community members
- **📊 Risk Assessment**: Provides clear risk scores and trust levels (HIGH/MEDIUM/LOW/CRITICAL)
- **⚡ Real-time Monitoring**: Continuously monitors Twitter for trigger phrases
- **🛡️ Safety First**: Focuses on protecting users from potential rug pulls and scams

## 🚀 How It Works

1. **Monitor**: Bot continuously scans Twitter replies for the trigger phrase "riddle me this"
2. **Identify**: Extracts the original tweet author (not the person who posted the trigger)
3. **Analyze**: Performs comprehensive account analysis including:
   - Account age and history
   - Follower/following ratios
   - Bio content analysis
   - Recent tweet patterns
   - Engagement metrics
4. **Verify**: Checks if account is vouched by trusted community members
5. **Report**: Posts a concise trustworthiness report as a reply

## 📋 Requirements

- Python 3.8+
- Twitter Developer Account (free tier sufficient)
- Virtual machine or server for hosting (Replit compatible)

## 🛠️ Installation & Setup

### Step 1: Clone the Repository

```bash
git clone https://github.com/yourusername/projectruggaurd.git
cd projectruggaurd
```

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 3: Set Up Twitter API Credentials

1. Visit [Twitter Developer Portal](https://developer.x.com/en/portal/petition/essential/basic-info)
2. Create a new app and generate API keys
3. Copy `.env.example` to `.env`:

   ```bash
   cp .env.example .env
   ```

4. Fill in your API credentials in the `.env` file:

   ```bash
   X_API_KEY=your_api_key_here
   X_API_SECRET=your_api_secret_here
   X_ACCESS_TOKEN=your_access_token_here
   X_ACCESS_TOKEN_SECRET=your_access_token_secret_here
   X_BEARER_TOKEN=your_bearer_token_here
   ```

### Step 4: Configure Bot Settings

Edit the `.env` file to customize:

- `BOT_USERNAME`: Your bot's Twitter username
- `TRIGGER_PHRASE`: Phrase that triggers analysis (default: "riddle me this")
- `LOG_LEVEL`: Logging verbosity (INFO, DEBUG, WARNING, ERROR)

### Step 5: Run the Bot

```bash
python main.py
```

## 🖥️ Replit Deployment

This bot is designed to be easily deployed on Replit:

1. **Import Project**:
   - Go to [Replit](https://replit.com)
   - Click "Create Repl" → "Import from GitHub"
   - Enter your repository URL

2. **Set Environment Variables**:
   - In Replit, go to "Secrets" tab
   - Add all variables from `.env.example`

3. **Run**:
   - Click the "Run" button
   - Bot will start monitoring automatically

## 📁 Project Structure

```bash
projectruggaurd/
├── main.py                    # Main bot entry point
├── requirements.txt           # Python dependencies
├── .env.example              # Environment variables template
├── README.md                 # This file
├── bot/               # Core bot functionality
│   ├── __init__.py
│   ├── twitter_api.py       # Twitter API interactions
│   ├── analysis.py          # Account analysis logic
│   └── report_generator.py  # Report formatting
└── config/                  # Configuration modules
    ├── __init__.py
    └── trusted_accounts.py   # Trusted accounts management
```

## 🔧 Architecture Overview

### Core Components

1. **TwitterAPIHandler** (`bot_logic/twitter_api.py`)
   - Manages all Twitter API interactions
   - Handles rate limiting and error recovery
   - Provides clean interfaces for common operations

2. **AccountAnalyzer** (`bot_logic/analysis.py`)
   - Performs comprehensive account analysis
   - Calculates risk scores based on multiple factors
   - Identifies suspicious patterns and positive indicators

3. **ReportGenerator** (`bot_logic/report_generator.py`)
   - Formats analysis results into readable reports
   - Ensures reports fit Twitter character limits
   - Provides different report types (standard, error, vouched)

4. **TrustedAccountsManager** (`config/trusted_accounts.py`)
   - Manages the list of trusted community accounts
   - Checks trust relationships and vouching status
   - Updates trusted list from GitHub repository

### Analysis Factors

The bot analyzes multiple factors to determine trustworthiness:

- **Account Age**: Newer accounts receive higher risk scores
- **Follower Ratios**: Suspicious follow patterns are flagged
- **Bio Analysis**: Scans for suspicious keywords vs. professional indicators
- **Engagement Patterns**: Analyzes tweet frequency and interaction quality
- **Content Quality**: Reviews recent tweets for spam indicators
- **Trust Network**: Verifies connections to trusted community members

## 🎯 Usage Examples

### Basic Trigger

```bash
User A: "Check out my new token! 🚀"
User B: "riddle me this"
Bot: "🔍 RUGGUARD ANALYSIS: @UserA
🟡 MEDIUM TRUST
📅 45d old | 👥 1.2K followers | 📊 2.1:1 ratio
⚠️ New account | Low engagement patterns
#RUGGUARD #DeFiSafety #DYOR"
```

### Trusted Account

```bash
User A: "New project announcement..."
User B: "riddle me this"
Bot: "🔍 RUGGUARD ANALYSIS: @UserA
🟢 HIGH TRUST
✅ Vouched by trusted network
👥 15K followers | 📅 2y old
🤝 5 trusted connections
✅ Professional bio content
#RUGGUARD #DeFiSafety #Trusted"
```

## ⚙️ Configuration Options

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `X_API_KEY` | Twitter API key | Required |
| `X_API_SECRET` | Twitter API secret | Required |
| `X_ACCESS_TOKEN` | Twitter access token | Required |
| `X_ACCESS_TOKEN_SECRET` | Twitter access token secret | Required |
| `X_BEARER_TOKEN` | Twitter bearer token | Required |
| `BOT_USERNAME` | Bot's Twitter username | projectrugguard |
| `TRIGGER_PHRASE` | Phrase that triggers analysis | riddle me this |
| `LOG_LEVEL` | Logging verbosity | INFO |

### Trusted Accounts List

The bot uses a curated list of trusted accounts from:
`https://github.com/devsyrem/turst-list/blob/main/list`

Accounts are considered "vouched" if they're followed by at least 2 trusted accounts.

## 🔒 Security & Privacy

- **No Data Storage**: Bot doesn't store personal data permanently
- **Public Information Only**: Only analyzes publicly available Twitter data
- **Rate Limiting**: Respects Twitter API rate limits
- **Error Handling**: Graceful handling of API errors and edge cases

## 🧪 Testing

### Manual Testing

1. Create a test tweet
2. Reply with "riddle me this"
3. Verify bot responds with analysis
4. Check analysis accuracy

### Automated Testing

```bash
# Run basic functionality tests
python -m pytest tests/ -v

# Test specific components
python -c "from bot_logic.analysis import AccountAnalyzer; print('Analysis module imported successfully')"
```

## 📊 Monitoring & Logs

The bot generates detailed logs including:

- API interactions and rate limiting
- Analysis results and scores
- Error handling and recovery
- Performance metrics

Logs are saved to `rugguard_bot.log`
