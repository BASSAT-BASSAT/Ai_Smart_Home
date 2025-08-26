# Step 1: Start with an official Python base image.
# 'python:3.9-slim' is a good choice because it's smaller than the full version.
FROM python:3.9-slim

# Step 2: Set the working directory inside the container.
# This is where all our commands will run from.
WORKDIR /app

# Step 3: Copy the requirements file into the container.
# We do this first because Docker caches layers. If the requirements don't change,
# Docker won't re-install them every time, which saves a lot of time.
COPY requirements.txt .

# Step 4: Install the Python libraries listed in the requirements file.
RUN pip install --no-cache-dir -r requirements.txt

# Step 5: Copy the rest of our application's code into the container.
COPY . .

# Step 6: Specify the command to run when the container starts.
# This tells the container to execute our Python script.
CMD ["python", "llm_service.py"]