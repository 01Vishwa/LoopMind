# AutoGraph Project Guide

## How to Run
1. Ensure you have Docker and Docker Compose installed.
2. Set up your `.env` file:
   ```bash
   cp .env.example .env
   # Edit .env with your OPENAI_API_KEY
   ```
3. Run the application:
   ```bash
   docker-compose up --build
   ```

## Happy Path Test
1. **Open Frontend**: Go to `http://localhost:8501`.
2. **Upload**: Use the sidebar to upload `data/sales_data.csv`.
3. **Analyze**: In the chat, ask "Show me sales over time".
4. **Observe**: The agent should generate a chart (e.g., Line or Bar).
5. **Feedback**: Click "👎 Bad" under the chart.
6. **Retry**: Ask the same question again.
7. **Verify**: The RL Engine should try a different chart type (exploration).

## Troubleshooting
- If backend fails with "OPENAI_API_KEY", check your `.env` file.
- If permission errors occur, ensure Docker has access to the drive.
