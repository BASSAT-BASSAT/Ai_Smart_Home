FROM python:3.9-slim

#the working directory inside the container.
WORKDIR /app

# Copy the requirements file into the container.
COPY requirements.txt .

# Install the Python libraries listed in the requirements file.
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of our application's code into the container.
COPY . .

# Specify the command to run when the container starts.
CMD ["python", "llm_service.py"]

