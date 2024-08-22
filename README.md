# Mortgage Rate API

This Flask application provides an API to retrieve historical mortgage rates for 15-year and 30-year terms.

## Setup Instructions

### Prerequisites

- Python 3.7+
- pip (Python package installer)

### Installation

1. Clone the repository:
   ```
   git clone https://github.com/your-username/mortgage-rate-api.git
   cd mortgage-rate-api
   ```

2. Create a virtual environment:
   ```
   python -m venv venv
   ```

3. Activate the virtual environment:
   - On Windows:
     ```
     venv\Scripts\activate
     ```
   - On macOS and Linux:
     ```
     source venv/bin/activate
     ```

4. Install the required packages:
   ```
   pip install -r requirements.txt
   ```

5. Create a `.env` file in the project root and add the following:
   ```
   FLASK_APP=run.py
   FLASK_ENV=development
   SECRET_KEY=your_secret_key_here
   ```
   Replace `your_secret_key_here` with a strong, randomly generated string.

### Database Setup

1. Initialize the database:
   ```
   flask db init
   flask db migrate -m "Initial migration"
   flask db upgrade
   ```

2. Load the mortgage rate data:
   ```
   flask load-data
   ```

### Running the Application

To run the application:

```
flask run
```

The API will be available at `http://127.0.0.1:5000/`.

## API Usage

### Get Token

To use the API, you first need to obtain a token:

```
curl -X POST http://127.0.0.1:5000/get_token
```

### Get Mortgage Rate

Use the token to request mortgage rates:

```
curl "http://127.0.0.1:5000/mortgage_rate?date=20220101&term=30&token=your_token_here"
```

Replace `20220101` with your desired date (format: YYYYMMDD), `30` with either 15 or 30 for the mortgage term, and `your_token_here` with the token you received.

### Revoke Token

To revoke a token:

```
curl -X POST "http://127.0.0.1:5000/revoke_token?token=your_token_here"
```

## Contributing

Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details on our code of conduct, and the process for submitting pull requests.

## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details.