# My Server Attack Map

This project is designed to monitor and visualize attacks on a server in real-time using an interactive map. It consists of a backend API for processing server logs and a frontend application for displaying the data.

## Project Structure

- **backend/**: Contains Python scripts for log parsing and the API.
  - **migrations/**: Database migration files 
  - **scripts/**: Log parsing and geolocation scripts.
  - **api.py**: FastAPI application.
  - **requirements.txt**: Python dependencies.

- **frontend/**: Contains the React application for the interactive map.
  - **src/**: Source code for the frontend application.
  - **public/**: Static assets for the frontend application.
  - **package.json**: Frontend project dependencies and configuration.
  - **Dockerfile**: Frontend container setup.

- **database/**: PostgreSQL setup.
  - **docker-compose.yml**: TimescaleDB container configuration.
  - **init.sql**: Optional initial schema.

- **.github/**: CI/CD setup.
  - **workflows/**: GitHub Actions workflows.
    - **deploy.yml**: Deployment configuration.

## Setup Instructions

1. **Clone the repository**:
   ```
   git clone https://github.com/kevlocburn/AttackVisualizer
   cd AttackVisualizer
   ```

2. **Backend Setup**:
   - Navigate to the `backend` directory.
   - Install dependencies:
     ```
     pip install -r requirements.txt
     ```
   - Run the API:
     ```
     python api.py
     ```

3. **Frontend Setup**:
   - Navigate to the `frontend` directory.
   - Install dependencies:
     ```
     npm install
     ```
   - Start the frontend application:
     ```
     npm start
     ```

4. **Database Setup**:
   - Navigate to the `database` directory.
   - Start the TimescaleDB container:
     ```
     docker-compose up
     ```

## Usage

Once the backend and frontend are running, you can access the interactive map through your web browser. The map will display real-time data on server attacks, including their origins and types.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request for any enhancements or bug fixes.

## License

This project is licensed under the MIT License.