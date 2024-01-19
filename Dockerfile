# Use an official Python runtime as a parent image
FROM python:3.10

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Make port 5000 available to the world outside this container
EXPOSE 7755

# Define environment variable
ENV FLASK_APP=core/server.py

# Reset the database
RUN rm core/store.sqlite3 && flask db upgrade -d core/migrations/

# Run app.py when the container launches
CMD ["bash", "run.sh"]
