# Simple Agent API

Welcome to the Simple Agent API: a robust, production-ready agentic system for serving Agents using a REST API. Use it to add agentic capabilities to your applications.

**Core Components:**
  * A **FastAPI server** for handling API requests.
  * A **PostgreSQL database** for storing Agent sessions, knowledge, and memories.
  * A set of **pre-built Agents** to use as a foundation for your projects.

## Support us

If you like this project, please give [Agno](https://agno.link/gh) a ⭐️.

## Table of Contents

- [Quickstart](#quickstart)
- [Development Setup](#development-setup)
- [Managing Python Dependencies](#managing-python-dependencies)
- [Community & Support](#community--support)

#### Prerequisites

* **Docker Desktop**: Ensure you have [Docker Desktop](https://www.docker.com/products/docker-desktop) installed and running on your system.

## Quickstart

Follow these steps to get your Agent API up and running:

1.  **Clone the Repository (if you haven't already)**:

    ```sh
    git clone https://github.com/agno-agi/agent-api.git
    cd agent-api
    ```

2.  **Configure API Keys**:
    We use GPT 4.1 as the default model, please set the `OPENAI_API_KEY` environment variable to get started.
    * **Option 1: Environment Variable (recommended for quickstart)**
      Export the `OPENAI_API_KEY` environment variable in your terminal:

      ```sh
      export OPENAI_API_KEY="YOUR_API_KEY_HERE"
      ```

      Docker Compose will automatically pick up this variable if it's set.

    * **Option 2: `.env` File**

      Create a new `.env` file by copying `.env.example` and add your API key there.

      ```sh
      cp example.env .env
      ```

    > **Note**: You can use any model provider, just update the agents in the `/agents` folder.

3.  **Start the Application**:
    Launch the services using Docker Compose:

    ```sh
    docker compose up -d
    ```

    This command starts:
    * The **FastAPI application**, serving on [http://localhost:8000](http://localhost:8000).
    * The **PostgreSQL database**, accessible on `localhost:5432`.

    Once started, you can:
    * Explore the API documentation via your browser at [http://localhost:8000/docs](http://localhost:8000/docs).

4.  **Test with Agno Playground**:
    * Open the [Agno Playground](https://app.agno.com/playground).
    * Add `http://localhost:8000` as a new endpoint. You can name it `Agent API` (or any name you prefer).
    * Select your newly added endpoint and start chatting with your Agents.

5.  **Stop the Application**:
    When you're done, stop the containers with:

    ```sh
    docker compose down
    ```

## Development Setup

To setup your local virtual environment:

1.  **Install `uv`**:
    We use `uv` for python environment and package management. Install it by following the instructions on the [official `uv` documentation](https://docs.astral.sh/uv/#getting-started) or use the command below for Unix-like systems:

    ```sh
    curl -LsSf https://astral.sh/uv/install.sh | sh
    ```

2.  **Create Virtual Environment & Install Dependencies**:
    Run the setup script. This will create a virtual environment (typically `.venv`) and install project dependencies:

    ```sh
    ./scripts/dev_setup.sh
    ```

3.  **Activate Virtual Environment**:
    Activate the created virtual environment:

    ```sh
    source .venv/bin/activate
    ```

    (On Windows, the activation command might differ, e.g., `.venv\Scripts\activate`)

## Managing Python Dependencies

If you need to add or update python dependencies:

1.  **Modify `pyproject.toml`**:

    Add or update your desired Python package dependencies in the `[dependencies]` section of the `pyproject.toml` file.

2.  **Generate `requirements.txt`**:
    The `requirements.txt` file is used to build the application image. After modifying `pyproject.toml`, regenerate `requirements.txt` using:

    ```sh
    ./scripts/generate_requirements.sh
    ```

    To upgrade all existing dependencies to their latest compatible versions, run:

    ```sh
    ./scripts/generate_requirements.sh upgrade
    ```

3.  **Rebuild Docker Images**:
    Rebuild your Docker images to include the updated dependencies:

    ```sh
    docker compose up -d --build
    ```

## Community & Support

Need help, have a question, or want to connect with the community?

*   📚 **[Read the Agno Docs](https://docs.agno.com)** for more in-depth information.
*   💬 **Chat with us on [Discord](https://agno.link/discord)** for live discussions.
*   ❓ **Ask a question on [Discourse](https://agno.link/community)** for community support.
*   🐛 **[Report an Issue](https://github.com/agno-agi/agent-api/issues)** on GitHub if you find a bug or have a feature request.
