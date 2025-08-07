# AI-Powered SEO & Content Optimization Platform

This project is an advanced web application designed to empower small and medium-sized businesses by automating their digital marketing processes and enhancing their SEO performance through the power of artificial intelligence. It leverages Playwright to conduct in-depth analyses of target websites, delivers comprehensive SEO reports, and utilizes Large Language Models like Gemini and Mistral to automatically generate tasks for content creation teams.

The application features a user-friendly interface built with Streamlit and securely stores all data in a Supabase database. Designed for easy deployment with Docker, this tool aims to give businesses a technological edge in SEO optimization and content strategy.

## 🚀 Key Features

*   **In-Depth SEO Analysis:** Automatically analyzes websites using Playwright to assess technical SEO, content quality, and performance metrics.
*   **Real-Time Reporting:** Instantly visualizes analysis results into an understandable and actionable SEO report.
*   **Instant SEO Score:** Provides a dynamic SEO score that summarizes the current health of the analyzed website.
*   **AI-Powered Task Generation:** Integrates with Gemini and Mistral APIs to automatically create specific tasks for article writers and product description writers based on identified SEO gaps.
*   **Secure Data Management:** Manages user data, analysis reports, and generated tasks securely and scalably using a Supabase database.
*   **Interactive Interface:** The web interface, developed with Streamlit, ensures that even users without technical expertise can easily navigate and use the platform.
*   **Easy Deployment:** Thanks to its Docker Compose setup, all services and dependencies can be launched with a single command.

## 🛠️ Tech Stack

*   **Frontend:** Streamlit
*   **Backend & AI:** Python, Gemini API, Mistral API
*   **Database:** Supabase
*   **Web Automation & Scraping:** Playwright
*   **Containerization:** Docker, Docker Compose

## 🔧 Installation and Setup

Follow these steps to run the project on your local machine.

**Prerequisites:**
*   [Docker](https://www.docker.com/get-started) and [Docker Compose](https://docs.docker.com/compose/install/) must be installed on your system.

**Steps:**

1.  **Clone the Repository:**
    ```bash
    git clone <YOUR_REPOSITORY_URL>
    cd <YOUR_PROJECT_DIRECTORY>
    ```

2.  **Set Up Environment Variables:**
    Create a file named `.env` in the project's root directory. Use the template below to populate the file with your own API keys and Supabase credentials.

    ```env
    # Your Supabase Project URL
    SUPABASE_URL=XXX

    # Your Supabase project's anon (public) key
    SUPABASE_KEY=XXXX

    # API base URL for Llama or other local models (optional)
    LLAMA_API_BASE_URL=http://127.0.0.1:8000

    # Your Mistral AI API key
    MISTRAL_API_KEY=XXXX

    # Custom API key for a user or another service (if needed)
    USER0_API_KEY=enter

    # Your Google Gemini API key
    GEMINI_API_KEY=XXXX
    ```

3.  **Launch the Application:**
    Run the following command to have Docker Compose build the images and start all services (application, database, etc.). The `--build` flag ensures that any changes in your code are applied.

    ```bash
    docker-compose up --build
    ```

4.  **Access the Application:**
    Once the setup is complete, you can access the application by navigating to `http://localhost:8501` (or the port you specified in your Docker Compose file) in your web browser.
