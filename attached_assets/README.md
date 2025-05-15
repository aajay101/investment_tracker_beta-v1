# Investor Dashboard

A comprehensive web-based dashboard for tracking investments, monitoring portfolio performance, and generating reports.

## Features

- User authentication (registration, login, logout)
- Portfolio management (add, edit, delete investments)
- Watchlist functionality (track stocks without investing)
- Real-time stock price data
- Portfolio performance tracking
- Report generation (PDF and Excel formats)
- Responsive design

## Installation

### Prerequisites

- Python 3.11 or higher
- pip or another package manager

### Setup

1. Clone the repository
2. Install dependencies:

```bash
pip install -e .
```

If using another package manager like `uv`:

```bash
uv pip install -e .
```

### Environment Variables (Optional)

You can configure the following environment variables:

- `SESSION_SECRET`: Secret key for session management (default: "dev-secret-key")
- `DATABASE_URL`: SQLAlchemy database URI (default: "sqlite:///investment_dashboard.db")

## Running the Application

### Development Server

```bash
python main.py
```

The application will be available at http://localhost:5000.

### Production Deployment

For production, use Gunicorn:

```bash
gunicorn -w 4 "main:app" --bind 0.0.0.0:5000
```

## Troubleshooting

### Common Issues

1. **Database errors**
   - Ensure the database file is writable
   - Check database connection settings

2. **Stock data not loading**
   - The application uses yfinance for stock data. If stock data is unavailable, check your internet connection.
   - For Indian stocks, the application appends '.NS' for NSE stocks if not already specified.

3. **Report generation fails**
   - Ensure you have write permissions in the temporary directory.

## License

This project is available under the MIT License. 