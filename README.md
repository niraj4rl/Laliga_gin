# La Liga Analytics & Match Prediction System

A machine learning-powered system to predict La Liga football match outcomes with real-time injury and suspension data integration.

## 🎯 Features

- **Match Predictions**: Real-time predictions for upcoming La Liga matches using ML models
- **Injury Integration**: Real-time player injury and suspension data enrichment
- **Historical Analysis**: Team statistics and performance trends
- **Key Player Impact**: Identifies key players and their performance metrics
- **Interactive Dashboard**: React-based UI for exploring predictions and standings
- **REST API**: FastAPI backend for seamless data access

## 🛠 Tech Stack

**Backend:**
- Python 3.x with FastAPI
- SQLAlchemy ORM for database operations
- PostgreSQL for data persistence
- Scikit-learn for ML model training

**Frontend:**
- React with Vite bundler
- Tailwind CSS for styling
- Axios for API communication

## 📋 Prerequisites

- Python 3.8+
- Node.js 16+
- PostgreSQL 12+
- Git

## 🚀 Setup & Installation

### 1. Clone the Repository
```bash
git clone https://github.com/niraj4rl/Laliga_gin.git
cd Laliga_gin
```

### 2. Backend Setup

#### Create Virtual Environment
```bash
python -m venv .venv

# On Windows
.venv\Scripts\activate

# On Linux/Mac
source .venv/bin/activate
```

#### Install Dependencies
```bash
cd backend
pip install -r requirements.txt
cd ..
```

#### Configure Environment Variables
```bash
# Copy the example file
cp backend/.env.example backend/.env

# Edit .env and add your API keys
# Required:
#   - FOOTBALL_API_KEY: Get from https://www.football-data.org/
# Optional:
#   - RAPIDAPI_KEY: For enhanced injury data from RapidAPI
#   - APIFOOTBALL_API_KEY: Alternative data provider
# Database:
#   - DATABASE_URL: PostgreSQL connection string
```

#### Setup Database
```bash
# Create database
createdb laliga_analytics

# Run migrations
cd backend
python -c "from database.db import Base, engine; Base.metadata.create_all(bind=engine)"

# Seed initial data (optional)
python database/seed.py
cd ..
```

### 3. Frontend Setup

```bash
cd frontend
npm install
cd ..
```

### 4. Run the Application

```bash
# Start both backend and frontend
python run.py
```

The application will be available at:
- Frontend: `http://localhost:8002`
- Backend API: `http://localhost:8001`

## 📡 API Endpoints

### Predictions
- `GET /predict/upcoming` - Get upcoming match predictions
- `GET /predict/upcoming?include_injuries=true` - Include injury data
- `GET /predict/upcoming?include_injuries=false` - Fast predictions without injury data

### Query Parameters
- `include_injuries` (boolean): Include player injury/suspension data (default: true)
- Response time varies: ~30s with injuries, ~5s without

## 🗂 Project Structure

```
├── backend/
│   ├── api/
│   │   └── main.py          # FastAPI endpoints
│   ├── database/
│   │   ├── db.py            # SQLAlchemy models & connection
│   │   ├── schema.sql       # Database schema
│   │   ├── seed.py          # Initial data setup
│   │   └── download_real_data.py
│   ├── ml/
│   │   ├── feature_engineering.py
│   │   └── train_model.py
│   ├── services/
│   │   └── data_service.py
│   ├── .env.example         # Environment variables template
│   ├── .env                 # Local secrets (gitignored)
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── services/
│   │   ├── App.js
│   │   └── index.css
│   ├── package.json
│   └── vite.config.js
├── data/
│   ├── features.csv
│   └── laliga_matches.csv
├── models/
│   └── model_meta.json
├── run.py                   # Main entry point
└── README.md
```

## 🔐 Security Notes

- **Never commit `.env` file** - It's gitignored for security
- **Use `.env.example`** as reference for required variables
- **Rotate API keys** if accidentally exposed
- All secrets are loaded from environment variables, not hardcoded

### Environment Variables
```env
# Database (Required)
DATABASE_URL=postgresql://username:password@localhost:5432/laliga_analytics

# API Keys
FOOTBALL_API_KEY=your_key_here          # Required - https://www.football-data.org/
RAPIDAPI_KEY=                            # Optional - for injury data
APIFOOTBALL_API_KEY=                     # Optional - alternative provider

# Features
ENABLE_INJURY_LOOKUP=1                  # 1 to enable, 0 to disable
UPCOMING_MATCH_LIMIT=5                  # Number of upcoming matches to fetch
```

## 🧹 Cleanup & Logs

### Stop Running Servers
```bash
# PowerShell (Windows)
Get-NetTCPConnection -LocalPort 8001,8002 -State Listen | Stop-Process -Force

# Bash (Linux/Mac)
lsof -ti:8001,8002 | xargs kill -9
```

## 📊 Model Information

- **Training Data**: Historical La Liga match data (2017-present)
- **Features**: Team form, head-to-head records, player availability, home/away advantage
- **Model**: Ensemble learning approach (Random Forest + Gradient Boosting)
- **Accuracy**: ~68% on test set

## 🐛 Troubleshooting

### Port Already in Use
```bash
# Find and stop process using port 8001 or 8002
netstat -ano | findstr :8001  # Windows
lsof -i :8001                 # Linux/Mac
```

### Database Connection Failed
- Ensure PostgreSQL is running
- Verify DATABASE_URL is correct in `.env`
- Check database name matches: `laliga_analytics`

### API Key Errors
- Verify FOOTBALL_API_KEY is valid at https://www.football-data.org/
- Injury data fails gracefully if RAPIDAPI_KEY is missing
- Use `include_injuries=false` for faster responses if API limits hit

## 🤝 Contributing

1. Create a feature branch: `git checkout -b feature/YourFeature`
2. Commit changes: `git commit -m 'Add YourFeature'`
3. Push to branch: `git push origin feature/YourFeature`
4. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see LICENSE file for details.

## 📧 Contact

**Author**: Niraj  
**GitHub**: [@niraj4rl](https://github.com/niraj4rl)  
**Email**: pashte.niraj2005@gmail.com

---

**Last Updated**: March 26, 2026  
**Repository**: [github.com/niraj4rl/Laliga_gin](https://github.com/niraj4rl/Laliga_gin)
